from pyspark.sql import SparkSession
import sys
import time

def neighbors(cell):
    """Gera as 8 coordenadas vizinhas de uma célula."""
    x, y = cell
    return [(x + dx, y + dy)
            for dx in [-1, 0, 1] for dy in [-1, 0, 1]
            if dx != 0 or dy != 0]

def life_step_spark(live_cells_rdd):
    """Executa uma geração do Jogo da Vida de forma distribuída."""
    neighbor_counts = live_cells_rdd.flatMap(lambda cell: [(n, 1) for n in neighbors(cell)])
    live_neighbor_sum = neighbor_counts.reduceByKey(lambda a, b: a + b)
    currently_alive_rdd = live_cells_rdd.map(lambda cell: (cell, True))
    joined_rdd = live_neighbor_sum.fullOuterJoin(currently_alive_rdd)

    def apply_rules(cell_data):
        _, (neighbor_count_opt, was_alive_opt) = cell_data
        live_neighbors = neighbor_count_opt or 0
        is_currently_alive = was_alive_opt is not None
        if not is_currently_alive and live_neighbors == 3:
            return True
        if is_currently_alive and (live_neighbors == 2 or live_neighbors == 3):
            return True
        return False

    return joined_rdd.filter(apply_rules).keys()

def correto(cells, tam):
    """Verifica se o resultado final corresponde ao padrão esperado."""
    vivos = set(cells)
    if len(vivos) != 5:
        return False
    alvo = {
        (tam-2, tam-1), (tam-1, tam), (tam, tam-2), (tam, tam-1), (tam, tam)
    }
    return alvo.issubset(vivos)

def main():
    """Função principal da aplicação Spark."""

    spark = SparkSession.builder.appName("GameOfLife").getOrCreate()
    sc = spark.sparkContext
    sc.setLogLevel("ERROR")

    try:
        powmin_str = sys.argv[-2]
        powmax_str = sys.argv[-1]
        powmin = int(powmin_str)
        powmax = int(powmax_str)
    except Exception as e:
        print("ERRO: Nao foi possivel extrair powmin e powmax dos argumentos da linha de comando.", file=sys.stderr)
        print(f"Argumentos recebidos (sys.argv): {sys.argv}", file=sys.stderr)
        print(f"Detalhe do erro: {e}", file=sys.stderr)
        spark.stop()
        sys.exit(1)

    print(f"Iniciando Game of Life para POWMIN = {powmin}, POWMAX = {powmax}")

    for p in range(powmin, powmax + 1):
        tam = 1 << p
        print(f"--- Processando para tam={tam} ---")
        
        seed = [(1, 2), (2, 3), (3, 1), (3, 2), (3, 3)]
        rdd = sc.parallelize(seed).cache()
        
        t0 = time.time()

        num_generations = 4 * (tam - 3)
        for _ in range(num_generations):
            new_rdd = life_step_spark(rdd).cache()
            # Forçar a materialização é importante
            new_rdd.count()
            rdd.unpersist()
            rdd = new_rdd
            
        t1 = time.time()
        
        result = sorted(rdd.collect())
        rdd.unpersist() # Limpa o último RDD
        
        print(f"--- Análise para tam={tam} ---")
        print(f"Células vivas encontradas: {len(result)}")
        
        if correto(result, tam):
            print("Resultado: **CORRETO** (padrão final esperado encontrado)")
        else:
            print("Resultado: **INCORRETO** (padrão final não encontrado)")
            
        print(f"Tempo total de processamento Spark: {t1-t0:.4f}s\n")

    spark.stop()

if __name__ == "__main__":
    main()