import sys
from parser import analizar_archivo

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Uso: python main.py <entrada.py> <salida.txt>")
        sys.exit(1)
    ruta_entrada = sys.argv[1]
    ruta_salida = sys.argv[2]
    analizar_archivo(ruta_entrada, ruta_salida)
