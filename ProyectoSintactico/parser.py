import sys
from lexer import (
    Scanner,
    ErrorLexico,
    Token,
)

class AbortarSintaxis(Exception):
    pass

class AnalizadorSintactico:
    def __init__(self, tokens, salida=sys.stdout):
        self.toks = tokens
        self.i = 0
        self.act = self.toks[0] if self.toks else Token("EOF","",1,1)
        self.salida = salida
        self.pila_indent = [1]
        self.ult_linea_sent = self.act.linea

    # utilidades
    def reportar_error(self, token, esperados=None, falla_indent=False):
        if falla_indent:
            msg = f"<{token.linea},{token.col}>Error sintactico: falla de indentacion"
        else:
            encontrado = "EOF" if token.tipo == "EOF" else (token.lexema if token.lexema != "" else token.tipo)
            exp = []
            if esperados:
                exp = [f"\"{e}\"" for e in esperados]
            msg = f"<{token.linea},{token.col}> Error sintactico: se encontro: \"{encontrado}\"; se esperaba: {', '.join(exp)}."
        self._emitir(msg)
        raise AbortarSintaxis()

    def _emitir(self, texto):
        if hasattr(self.salida, "write"):
            self.salida.write(texto + "\n")
        else:
            print(texto)

    def avanzar(self):
        if self.i < len(self.toks)-1:
            self.i += 1
            self.act = self.toks[self.i]

    def emparejar(self, tipos, mostrar=None):
        if isinstance(tipos, str):
            tipos = [tipos]
        if self.act.tipo in tipos or self.act.lexema in tipos:
            tok = self.act
            self.avanzar()
            return tok
        else:
            esperados = mostrar if mostrar else tipos
            self.reportar_error(self.act, esperados=esperados)

    def en_limite_de_linea(self):
        # Detecta si comenzó una nueva linea con respecto a la ultima sentencia
        return self.act.linea > self.ult_linea_sent

    # punto de entrada
    def analizar(self):
        try:
            self.programa()
            self._emitir("El analisis sintactico ha finalizado exitosamente.")
        except AbortarSintaxis:
            return
        except ErrorLexico as le:
            self._emitir(str(le))

    # gramática
    def programa(self):
        # secuencia de sentencias hasta EOF
        while self.act.tipo != "EOF":
            self.sentencia()

    # gestion de indentacion para sentencias compuestas
    def requerir_indentacion_si_necesaria(self):
        if self.act.linea == self.ult_linea_sent:
            # debe comenzar en una nueva línea tras ':'
            self.reportar_error(self.act, falla_indent=True)
        # la siguiente sentencia debe estar más indentada que el tope de la pila
        col = self.act.col
        if col <= self.pila_indent[-1]:
            self.reportar_error(self.act, falla_indent=True)
        # apilar indentacion
        self.pila_indent.append(col)
        self.ult_linea_sent = self.act.linea

    def intentar_dedentar(self):
        # si la linea aumento y la columna actual < tope, hay dedent
        while self.act.linea > self.ult_linea_sent and self.act.col < self.pila_indent[-1]:
            self.pila_indent.pop()
            if len(self.pila_indent) == 0:
                self.reportar_error(self.act, falla_indent=True)

    def consumir_contexto_nueva_linea(self):
        if self.act.linea == self.ult_linea_sent:
            # Para el subconjunto, se exige nueva linea entre sentencias
            pass
        else:
            self.intentar_dedentar()
            self.ult_linea_sent = self.act.linea

    def sentencia(self):
        # Alinear contexto de nueva linea / indentacion
        self.consumir_contexto_nueva_linea()

        # Sentencias compuestas primero
        if self.act.lexema == "def":
            self.definicion_funcion()
            return
        if self.act.lexema == "if":
            self.sentencia_if()
            return
        if self.act.lexema == "while":
            self.sentencia_while()
            return
        if self.act.lexema == "for":
            self.sentencia_for()
            return
        # Sentencias simples
        self.sentencia_simple()

    # sentencias simples
    def sentencia_simple(self):
        if self.act.lexema in ("pass","break","continue"):
            self.avanzar()
            return
        if self.act.lexema == "return":
            self.avanzar()
            # expresion opcional en la misma línea
            if self.act.tipo != "EOF" and self.act.linea == self.ult_linea_sent:
                self.expresion()
            return
        # asignacion o expresion
        self.sentencia_expresion()

    def sentencia_expresion(self):
        # destino ('=' expr) | expresion
        # Primero parsea la izquierda; si sigue '=', es asignacion (posibles cadenas: a=b=c)
        self.lista_expresiones()
        while self.act.lexema == "=":
            self.emparejar("=")
            self.lista_expresiones()

    # sentencias compuestas
    def definicion_funcion(self):
        self.emparejar("def")
        self.emparejar("id", mostrar=["identificador"])
        self.emparejar("tk_par_izq", mostrar=["("])
        if self.act.tipo != "tk_par_der":
            self.parametros()
        self.emparejar("tk_par_der", mostrar=[")"])
        self.emparejar("tk_dos_puntos", mostrar=[":"])
        # bloque
        self.requerir_indentacion_si_necesaria()
        self.bloque()

    def sentencia_if(self):
        self.emparejar("if")
        self.expresion()
        self.emparejar("tk_dos_puntos", mostrar=[":"])
        self.requerir_indentacion_si_necesaria()
        self.bloque()
        while self.act.lexema == "elif":
            self.emparejar("elif")
            self.expresion()
            self.emparejar("tk_dos_puntos", mostrar=[":"])
            self.requerir_indentacion_si_necesaria()
            self.bloque()
        if self.act.lexema == "else":
            self.emparejar("else")
            self.emparejar("tk_dos_puntos", mostrar=[":"])
            self.requerir_indentacion_si_necesaria()
            self.bloque()

    def sentencia_while(self):
        self.emparejar("while")
        self.expresion()
        self.emparejar("tk_dos_puntos", mostrar=[":"])
        self.requerir_indentacion_si_necesaria()
        self.bloque()

    def sentencia_for(self):
        self.emparejar("for")
        self.emparejar("id", mostrar=["identificador"])
        self.emparejar("in")
        self.expresion()
        self.emparejar("tk_dos_puntos", mostrar=[":"])
        self.requerir_indentacion_si_necesaria()
        self.bloque()

    def bloque(self):
        # Una o mas sentencias con la misma indentacion
        linea_base = self.act.linea
        col_base = self.pila_indent[-1]
        while self.act.tipo != "EOF" and self.act.col == col_base and self.act.linea >= linea_base:
            self.sentencia()
            if self.act.tipo == "EOF" or self.act.col < col_base:
                break
        # dedent al final del bloque
        if self.pila_indent and self.pila_indent[-1] == col_base:
            self.pila_indent.pop()

    # --- parametros y argumentos ---
    def parametros(self):
        # param (',' param)* [',']
        self.parametro()
        while self.act.lexema == ",":
            self.emparejar(",")
            if self.act.tipo == "tk_par_der":
                break
            self.parametro()

    def parametro(self):
        self.emparejar("id", mostrar=["identificador"])
        if self.act.lexema == ":":
            self.emparejar(":")
            self.tipo_anotado()

    def tipo_anotado(self):
        # tipo simple: id  |  lista tipada: [ id ]
        if self.act.lexema == "[":
            self.emparejar("[")
            self.emparejar("id", mostrar=["tipo/identificador"])
            # si hay coma aquí, el enunciado espera que falte ']' (caso de prueba)
            if self.act.lexema == ",":
                self.reportar_error(self.act, esperados=["]"])
            self.emparejar("]", mostrar=["]"])
        else:
            self.emparejar("id", mostrar=["tipo/identificador"])

    # expresiones
    def lista_expresiones(self):
        # lista de expresiones separadas por coma (para lados de asignación)
        self.expresion()
        while self.act.lexema == ",":
            self.emparejar(",")
            self.expresion()
        return True

    def expresion(self):
        return self.expr_or()

    def expr_or(self):
        self.expr_and()
        while self.act.lexema == "or":
            self.emparejar("or")
            self.expr_and()

    def expr_and(self):
        self.expr_not()
        while self.act.lexema == "and":
            self.emparejar("and")
            self.expr_not()

    def expr_not(self):
        if self.act.lexema == "not":
            self.emparejar("not")
            self.expr_not()
        else:
            self.comparacion()

    def comparacion(self):
        self.expr_arit()
        while self.act.lexema in ("==","!=", "<",">","<=",">=","in","is"):
            self.avanzar()
            self.expr_arit()

    def expr_arit(self):
        self.termino()
        while self.act.lexema in ("+","-"):
            self.avanzar()
            self.termino()

    def termino(self):
        self.factor()
        while self.act.lexema in ("*","/","%"):
            self.avanzar()
            self.factor()

    def factor(self):
        if self.act.lexema in ("+","-"):
            self.avanzar()
            self.factor()
            return
        self.potencia()

    def potencia(self):
        self.atomo()
        # trailers: llamadas, indexación y atributos
        while True:
            if self.act.lexema == "(":
                self.emparejar("(")
                if self.act.lexema != ")":
                    self.lista_argumentos()
                self.emparejar(")", mostrar=[")"])
            elif self.act.lexema == "[":
                self.emparejar("[")
                self.expresion()
                self.emparejar("]", mostrar=["]"])
            elif self.act.lexema == ".":
                self.emparejar(".")
                self.emparejar("id", mostrar=["identificador"])
            else:
                break

    def atomo(self):
        tok = self.act
        if tok.tipo == "id" or tok.tipo in {"tk_entero","tk_cadena"} or tok.lexema in {"True","False","None"}:
            self.avanzar()
            return
        if tok.lexema == "(":
            self.emparejar("(")
            if self.act.lexema == ")":
                self.emparejar(")")
                return
            self.expresion()
            self.emparejar(")", mostrar=[")"])
            return
        if tok.lexema == "[":
            # literal de lista: [ (expr (',' expr)* [','])? ]
            self.emparejar("[")
            if self.act.lexema != "]":
                self.expresion()
                while self.act.lexema == ",":
                    self.emparejar(",")
                    if self.act.lexema == "]":
                        break
                    self.expresion()
            self.emparejar("]", mostrar=["]"])
            return
        if tok.lexema == "lambda":
            self.expresion_lambda()
            return
        # inesperado
        self.reportar_error(tok, esperados=["id","num","cadena","(","[","lambda","True","False","None"])

    def lista_argumentos(self):
        # expr (',' expr)* [',']
        self.expresion()
        while self.act.lexema == ",":
            self.emparejar(",")
            if self.act.lexema == ")":
                break
            self.expresion()
        # Validación para mensaje esperado del enunciado
        if self.act.lexema not in (")", ","):
            self.reportar_error(self.act, esperados=[")", ","])

    def expresion_lambda(self):
        self.emparejar("lambda")
        # parámetros opcionales
        if self.act.lexema != ":":
            self.parametros_lambda()
        self.emparejar(":", mostrar=[":"])
        self.expresion()

    def parametros_lambda(self):
        self.emparejar("id", mostrar=["identificador"])
        while self.act.lexema == ",":
            self.emparejar(",")
            self.emparejar("id", mostrar=["identificador"])


def analizar_archivo(ruta_entrada, ruta_salida):
    with open(ruta_entrada, "r", encoding="utf-8") as f:
        texto = f.read()
    try:
        sc = Scanner(texto)
        sc.analizar()
    except ErrorLexico as le:
        with open(ruta_salida, "w", encoding="utf-8") as out:
            out.write(str(le))
        return
    with open(ruta_salida, "w", encoding="utf-8") as out:
        p = AnalizadorSintactico(sc.tokens, salida=out)
        p.analizar()
