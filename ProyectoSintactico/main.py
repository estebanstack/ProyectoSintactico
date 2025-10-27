import sys
from parser import analizar_archivo

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python main.py <archivo_entrada.py>")
        sys.exit(1)

    ruta_entrada = sys.argv[1]
    ruta_salida = "salida.txt"  

    print(f"Analizando '{ruta_entrada}'... El resultado se guardara en '{ruta_salida}'")


    analizar_archivo(ruta_entrada, ruta_salida)

    
    with open(ruta_salida, "r", encoding="utf-8") as f:
        print("\n--- Resultado del analisis ---")
        print(f.read())
