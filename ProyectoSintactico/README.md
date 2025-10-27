# Analizador Sintáctico del Lenguaje Python

## Descripción general

Este proyecto implementa un **Analizador Sintáctico** para un subconjunto del lenguaje **Python**, basado en un **Analizador Léxico** (lexer) que produce los tokens necesarios para el análisis.  
El objetivo es detectar y reportar **errores sintácticos** en un archivo `.py`, simulando el comportamiento de un compilador real, pero **sin usar herramientas externas** (como ANTLR, PLY, YACC o NLTK).

El sistema está dividido en tres módulos:
1. **`lexer.py`** → Analizador léxico (escáner)
2. **`parser.py`** → Analizador sintáctico (parser descendente predictivo)
3. **`main.py`** → Punto de entrada que integra ambos módulos

---

## Funcionamiento general del sistema

### 1. `lexer.py` – Analizador léxico

El **lexer** es el encargado de leer el archivo fuente (`.py`) carácter por carácter y dividirlo en **tokens**, que son las unidades básicas del lenguaje (palabras clave, identificadores, operadores, etc.).

**Componentes principales:**
- `Buffer` → controla la lectura de caracteres y las posiciones (línea, columna).
- `Automatas` → cada tipo de token tiene un autómata finito determinista:
  - `AFDIdentificador` (identificadores y palabras reservadas)
  - `AFDEntero` (números enteros)
  - `AFDCadena` (cadenas `"..."` o `'...'`)
  - `AFDOperador` (símbolos como `+`, `-`, `(`, `)`, etc.)
- `Scanner` → recorre el texto y aplica los autómatas en orden hasta reconocer un token.

**Salida del lexer:** una lista de objetos `Token`, cada uno con:
```python
Token(tipo='id', lexema='variable', linea=3, col=5)
```

Al final se agrega un token `EOF` (fin de archivo) para señalar el final de la entrada.

---

### 2. `parser.py` – Analizador sintáctico

El **parser** recibe la lista de tokens generada por el lexer y verifica si estos forman una **estructura sintácticamente válida** según las reglas de una **gramática simplificada de Python**.

El parser está implementado como un **analizador descendente predictivo recursivo**, es decir:
- Cada **no terminal** de la gramática se implementa como una **función**.
- El parser **mira un solo token de lookahead** (anticipación) para decidir qué regla aplicar.
- No necesita retroceder (*no backtracking*), por lo tanto se comporta como un **LL(1)** (una entrada, un token de anticipación).

#### Gramática
```
programa        → sentencia*
sentencia       → definicion_funcion | sentencia_if | sentencia_while | sentencia_for | sentencia_simple
sentencia_simple→ 'pass' | 'break' | 'continue' | 'return' expresion? | sentencia_expresion
sentencia_expresion → expresion ('=' expresion)?
definicion_funcion  → 'def' id '(' parametros? ')' ':' bloque
sentencia_if    → 'if' expresion ':' bloque ('elif' expresion ':' bloque)* ('else' ':' bloque)?
bloque          → sentencia+
expresion       → expr_or
expr_or         → expr_and ('or' expr_and)*
expr_and        → expr_not ('and' expr_not)*
expr_not        → 'not' expr_not | comparacion
comparacion     → expr_arit (op_relacional expr_arit)*
expr_arit       → termino (('+'|'-') termino)*
termino         → factor (('*'|'/'|'%') factor)*
factor          → ('+'|'-') factor | potencia
potencia        → atomo trailer*
atomo           → id | num | cadena | '(' expresion ')' | '[' lista ']' | 'lambda' ...
```

#### Bloques y sangría (indentación)
A diferencia de muchos lenguajes, Python **usa la indentación para definir bloques**.  
Aquí se simula esa característica usando una **pila de indentación (`pila_indent`)** que controla cuántos espacios hay al inicio de cada línea.

Si el bloque siguiente no está correctamente indentado, se reporta:
```
<linea,col>Error sintactico: falla de indentacion
```

---

### 3. `main.py` – Programa principal

Este archivo se encarga de la **interacción** con el usuario o con la consola.

```bash
python main.py entrada.py
```

Pasos:
1. Lee el archivo de entrada (`entrada.py`).
2. Pasa el código al **lexer** para obtener los tokens.
3. Envía los tokens al **parser** para analizarlos.
4. Crea automáticamente un archivo de salida llamado **`salida.txt`** con el resultado del análisis.
5. Muestra también el resultado directamente por consola.

#### Ejemplo de uso

```bash
python main.py prueba.py
```

#### Salida por consola:
```
Analizando 'prueba.py'... El resultado se guardará en 'salida.txt'

--- Resultado del análisis ---
El analisis sintactico ha finalizado exitosamente.
```

#### Archivo generado:
`salida.txt`

- Si **no hay errores**:
  ```
  El analisis sintactico ha finalizado exitosamente.
  ```

- Si **hay errores**:
  ```
  <linea,col> Error sintactico: se encontro: ":"; se esperaba: ")", ",".
  ```

---

## Implementacion de Conjuntos

El parser implementa los conceptos de **gramáticas LL(1)**, como los conjuntos de **PRIMEROS**, **SIGUIENTES** y **PREDICCIÓN**, pero de forma **implícita** dentro del código.

### 🔹 PRIMEROS
En cada función que representa un no terminal, las condiciones `if` definen su conjunto de **PRIMEROS**.

### 🔹 SIGUIENTES
Las producciones que pueden repetirse o vaciarse (ε) usan **bucles `while`** para simular los conjuntos FOLLOW, deteniéndose cuando el token ya no pertenece a FIRST de la repetición.

### 🔹 PREDICCIÓN
Cada `if` o `elif` del parser implementa la **decisión predictiva** del conjunto FIRST/PREDICCIÓN.  
El token actual (`self.act`) actúa como *lookahead* de 1 símbolo.

---

## ¿Es una gramática LL(1)?

**Sí, el parser sigue el estilo LL(1)** porque:
- Usa **un token de lookahead**.
- No tiene **retroceso** (*backtracking*).
- Las reglas están **factorizadas** y sin recursión izquierda.
- Las decisiones se toman con **predicciones deterministas**.

Pero **no es LL(1) estricta** porque:
1. La indentación depende del contexto (no puramente libre de contexto).
2. Algunas construcciones (como asignaciones) requieren leer parte de la producción para decidir.

---

## Ejemplo de ejecución

### Entrada
```python
# Search in a list
def contains(items:[int], x:int):
    if contains([4, 8, 15, 16,
    23]: 15):
        print("Item found!")  # Prints this
    else:
        print("Item not found.")
```

### Salida
```
<4,8> Error sintactico: se encontro: ":"; se esperaba: ")", ",".
```

---

## Conclusión

Este proyecto aplica de forma práctica un **análisis sintáctico predictivo LL(1)**:
- Parser recursivo sin backtracking.
- Uso de **PRIMEROS**, **SIGUIENTES** y **PREDICCIÓN** de forma implicita.
- Reporte de errores sintácticos detallado y manejo de indentación al estilo Python.
