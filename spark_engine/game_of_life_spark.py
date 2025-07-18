from pyspark.sql import SparkSession
import sys

def neighbors(cell):
    x, y, state = cell
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            if dx or dy:
                yield (x + dx, y + dy), 1

def parse_line(line):
    # Recebe "x,y,state"
    x, y, s = map(int, line.split(','))
    return (x, y, s)

def life_step(cells_rdd):
    # cells_rdd: RDD[(x,y,state)]
    neighbor_counts = (
        cells_rdd.flatMap(neighbors)
        .reduceByKey(lambda a, b: a + b)
    )
    alive = cells_rdd.filter(lambda c: c[2] == 1).map(lambda c: ((c[0],c[1]),1))
    # União contagens
    joined = neighbor_counts.fullOuterJoin(alive)
    
    def rule(item):
        (x,y), (cnt, is_alive) = item
        cnt = cnt or 0
        is_alive = is_alive or 0
        alive_next = 1 if (is_alive == 1 and cnt in (2,3)) or (is_alive == 0 and cnt == 3) else 0
        return (x, y, alive_next)
    
    return joined.map(rule)

if __name__ == "__main__":
    try:
        powmin = int(sys.argv[-2])
        powmax = int(sys.argv[-1])
    except Exception:
        raise ValueError(f"Esperava dois inteiros como os dois últimos args, mas recebi: {sys.argv}")

    spark = SparkSession.builder.appName("GameOfLifeEngine").getOrCreate()
    sc = spark.sparkContext
    
    seed = [(1,2,1), (2,3,1), (3,1,1), (3,2,1), (3,3,1)]
    cells = sc.parallelize(seed)
    
    for _ in range(powmin, powmax):
        cells = life_step(cells)
    
    result = cells.filter(lambda c: c[2] == 1).collect()
    for x,y,_ in result:
        print(f"{x},{y},1")
    
    spark.stop()