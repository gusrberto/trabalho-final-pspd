#include <stdio.h>
#include <stdlib.h>
#include <sys/time.h>
#include <mpi.h>
#include <omp.h>

// Macro para indexar o array 1D como 2D, considerando as bordas
#define ind2d(i, j) (i) * (tam + 2) + (j)

// Função para medir o tempo
double wall_time(void) {
    struct timeval tv;
    struct timezone tz;
    gettimeofday(&tv, &tz);
    return (tv.tv_sec + tv.tv_usec / 1000000.0);
}

// Função que calcula uma geração (vida) em uma porção do tabuleiro
void UmaVida(int* tabulIn, int* tabulOut, int tam, int start_row, int end_row) {
    int i, j, vizviv;

    // As variáveis i, j, vizviv são privadas para cada thread, evitando condições de corrida
    #pragma omp parallel for private(i, j, vizviv)
    for (i = start_row; i <= end_row; i++) {
        for (j = 1; j <= tam; j++) {
            vizviv = tabulIn[ind2d(i - 1, j - 1)] + tabulIn[ind2d(i - 1, j)] +
                     tabulIn[ind2d(i - 1, j + 1)] + tabulIn[ind2d(i, j - 1)] +
                     tabulIn[ind2d(i, j + 1)] + tabulIn[ind2d(i + 1, j - 1)] +
                     tabulIn[ind2d(i + 1, j)] + tabulIn[ind2d(i + 1, j + 1)];

            if (tabulIn[ind2d(i, j)] && vizviv < 2)
                tabulOut[ind2d(i, j)] = 0;
            else if (tabulIn[ind2d(i, j)] && vizviv > 3)
                tabulOut[ind2d(i, j)] = 0;
            else if (!tabulIn[ind2d(i, j)] && vizviv == 3)
                tabulOut[ind2d(i, j)] = 1;
            else
                tabulOut[ind2d(i, j)] = tabulIn[ind2d(i, j)];
        }
    }
}

// Função para verificar se o resultado final está correto (executada apenas pelo rank 0)
int Correto(int* tabul, int tam) {
    int ij, cnt = 0;
    for (ij = 0; ij < (tam + 2) * (tam + 2); ij++)
        cnt = cnt + tabul[ij];
    
    return (cnt == 5 && tabul[ind2d(tam - 2, tam - 1)] &&
            tabul[ind2d(tam - 1, tam)] && tabul[ind2d(tam, tam - 2)] &&
            tabul[ind2d(tam, tam - 1)] && tabul[ind2d(tam, tam)]);
}

int main(int argc, char* argv[]) {
    int pow, i, tam;
    int *tabulIn, *tabulOut, *temp_ptr;
    double t0, t1, t2, t3;
    
    int rank, size;
    int powmin, powmax;

    MPI_Init(&argc, &argv);
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    MPI_Comm_size(MPI_COMM_WORLD, &size);

    if (rank == 0) {
        if (argc != 3) {
            fprintf(stderr, "Uso: %s <POWMIN> <POWMAX>\n", argv[0]);
            MPI_Abort(MPI_COMM_WORLD, 1);
        }
        powmin = atoi(argv[1]);
        powmax = atoi(argv[2]);
    }

    MPI_Bcast(&powmin, 1, MPI_INT, 0, MPI_COMM_WORLD);
    MPI_Bcast(&powmax, 1, MPI_INT, 0, MPI_COMM_WORLD);

    for (pow = powmin; pow <= powmax; pow++) {
        tam = 1 << pow;

        int rows_per_proc = tam / size;
        int my_start_row = rank * rows_per_proc + 1;
        int my_end_row = (rank + 1) * rows_per_proc;
        if (rank == size - 1) {
            my_end_row = tam;
        }
        int my_num_rows = my_end_row - my_start_row + 1;
        
        tabulIn = (int*)calloc((my_num_rows + 2) * (tam + 2), sizeof(int));
        tabulOut = (int*)calloc((my_num_rows + 2) * (tam + 2), sizeof(int));
        
        if (my_start_row <= 1 && 1 <= my_end_row) tabulIn[ind2d(1 - my_start_row + 1, 2)] = 1;
        if (my_start_row <= 2 && 2 <= my_end_row) tabulIn[ind2d(2 - my_start_row + 1, 3)] = 1;
        if (my_start_row <= 3 && 3 <= my_end_row) tabulIn[ind2d(3 - my_start_row + 1, 1)] = 1;
        if (my_start_row <= 3 && 3 <= my_end_row) tabulIn[ind2d(3 - my_start_row + 1, 2)] = 1;
        if (my_start_row <= 3 && 3 <= my_end_row) tabulIn[ind2d(3 - my_start_row + 1, 3)] = 1;

        if (rank == 0) t0 = wall_time();
        MPI_Barrier(MPI_COMM_WORLD);
        if (rank == 0) t1 = wall_time();

        for (i = 0; i < 4 * (tam - 3); i++) {
            int upper_neighbor = (rank == 0) ? MPI_PROC_NULL : rank - 1;
            int lower_neighbor = (rank == size - 1) ? MPI_PROC_NULL : rank + 1;

            MPI_Sendrecv(&tabulIn[ind2d(1, 0)], tam + 2, MPI_INT, upper_neighbor, 0,
                         &tabulIn[ind2d(0, 0)], tam + 2, MPI_INT, upper_neighbor, 0,
                         MPI_COMM_WORLD, MPI_STATUS_IGNORE);

            MPI_Sendrecv(&tabulIn[ind2d(my_num_rows, 0)], tam + 2, MPI_INT, lower_neighbor, 0,
                         &tabulIn[ind2d(my_num_rows + 1, 0)], tam + 2, MPI_INT, lower_neighbor, 0,
                         MPI_COMM_WORLD, MPI_STATUS_IGNORE);

            UmaVida(tabulIn, tabulOut, tam, 1, my_num_rows);

            temp_ptr = tabulIn;
            tabulIn = tabulOut;
            tabulOut = temp_ptr;
        }

        MPI_Barrier(MPI_COMM_WORLD);
        if (rank == 0) t2 = wall_time();

        int *recvcounts = NULL, *displs = NULL;
        int* final_tabul = NULL;

        if (rank == 0) {
            final_tabul = (int*)calloc((tam + 2) * (tam + 2), sizeof(int));
            recvcounts = (int*)malloc(size * sizeof(int));
            displs = (int*)malloc(size * sizeof(int));
        }
        
        int sendcount = my_num_rows * (tam + 2);
        MPI_Gather(&sendcount, 1, MPI_INT, recvcounts, 1, MPI_INT, 0, MPI_COMM_WORLD);

        if (rank == 0) {
            displs[0] = 0;
            for (int r = 1; r < size; r++) {
                displs[r] = displs[r - 1] + recvcounts[r - 1];
            }
        }
        
        MPI_Gatherv(&tabulIn[ind2d(1, 0)], sendcount, MPI_INT,
                    &final_tabul[ind2d(1, 0)], recvcounts, displs, MPI_INT,
                    0, MPI_COMM_WORLD);

        if (rank == 0) {
            if (Correto(final_tabul, tam)) {
                printf("**RESULTADO CORRETO** para tam=%d\n", tam);
            } else {
                printf("**RESULTADO ERRADO** para tam=%d\n", tam);
            }

            t3 = wall_time();
            printf("tam=%d; ranks=%d; threads=%d; tempos: init=%7.7f, comp=%7.7f, fim=%7.7f, tot=%7.7f\n",
                   tam, size, omp_get_max_threads(), t1 - t0, t2 - t1, t3 - t2, t3 - t0);
            
            free(final_tabul);
            free(recvcounts);
            free(displs);
        }

        free(tabulIn);
        free(tabulOut);
    }

    MPI_Finalize();
    return 0;
}