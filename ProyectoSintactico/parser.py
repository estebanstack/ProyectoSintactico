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
        self.act = self.toks[0] if self.toks else Token("EOF", "", 1, 1)
        self.salida = salida
        self.pila_indent = [1]
        self.ult_linea_sent = self.act.linea

    # -------------------- utilidades --------------------
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
        if self.i < len(self.toks) - 1:
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
        return self.act.linea > self.ult_linea_sent

    # -------------------- punto de entrada --------------------
    def analizar(self):
        try:
            self.programa()
            self._emitir("El analisis sintactico ha finalizado exitosamente.")
        except AbortarSintaxis:
            # igual imprimimos los conjuntos teóricos para referencia
            self.imprimir_conjuntos_teoricos()
            return
        except ErrorLexico as le:
            self._emitir(str(le))
            self.imprimir_conjuntos_teoricos()
            return

        # si todo ok, también imprimimos conjuntos
        self.imprimir_conjuntos_teoricos()

    # -------------------- gramática --------------------
    def programa(self):
        while self.act.tipo != "EOF":
            self.sentencia()

    # gestión indentación
    def requerir_indentacion_si_necesaria(self):
        if self.act.linea == self.ult_linea_sent:
            self.reportar_error(self.act, falla_indent=True)
        col = self.act.col
        if col <= self.pila_indent[-1]:
            self.reportar_error(self.act, falla_indent=True)
        self.pila_indent.append(col)
        self.ult_linea_sent = self.act.linea

    def intentar_dedentar(self):
        while self.act.linea > self.ult_linea_sent and self.act.col < self.pila_indent[-1]:
            self.pila_indent.pop()
            if len(self.pila_indent) == 0:
                self.reportar_error(self.act, falla_indent=True)

    def consumir_contexto_nueva_linea(self):
        if self.act.linea == self.ult_linea_sent:
            pass
        else:
            self.intentar_dedentar()
            self.ult_linea_sent = self.act.linea

    def sentencia(self):
        self.consumir_contexto_nueva_linea()

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
        self.sentencia_simple()

    # sentencias simples (incluye print)
    def sentencia_simple(self):
        if self.act.lexema in ("pass", "break", "continue"):
            self.avanzar()
            return

        if self.act.lexema == "return":
            self.avanzar()
            if self.act.tipo != "EOF" and self.act.linea == self.ult_linea_sent:
                self.expresion()
            return

        if self.act.lexema == "print":
            self.avanzar()
            self.emparejar("(", mostrar=["("])
            if self.act.lexema != ")":
                self.lista_argumentos()
            self.emparejar(")", mostrar=[")"])
            return

        self.sentencia_expresion()

    def sentencia_expresion(self):
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
        linea_base = self.act.linea
        col_base = self.pila_indent[-1]
        while self.act.tipo != "EOF" and self.act.col == col_base and self.act.linea >= linea_base:
            self.sentencia()
            if self.act.tipo == "EOF" or self.act.col < col_base:
                break
        if self.pila_indent and self.pila_indent[-1] == col_base:
            self.pila_indent.pop()

    # --- parametros y argumentos ---
    def parametros(self):
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
        if self.act.lexema == "[":
            self.emparejar("[")
            self.emparejar("id", mostrar=["tipo/identificador"])
            if self.act.lexema == ",":
                self.reportar_error(self.act, esperados=["]"])
            self.emparejar("]", mostrar=["]"])
        else:
            self.emparejar("id", mostrar=["tipo/identificador"])

    # expresiones
    def lista_expresiones(self):
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
        while self.act.lexema in ("==", "!=", "<", ">", "<=", ">=", "in", "is"):
            self.avanzar()
            self.expr_arit()

    def expr_arit(self):
        self.termino()
        while self.act.lexema in ("+", "-"):
            self.avanzar()
            self.termino()

    def termino(self):
        self.factor()
        while self.act.lexema in ("*", "/", "%"):
            self.avanzar()
            self.factor()

    def factor(self):
        if self.act.lexema in ("+", "-"):
            self.avanzar()
            self.factor()
            return
        self.potencia()

    def potencia(self):
        
        self.atomo()

        
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

        # 3) potencia '**' (asociativa a la derecha)
        if self.act.lexema == "**":
            self.emparejar("**")
            self.factor()

    def atomo(self):
        tok = self.act
        if tok.tipo in {"id", "tk_entero", "tk_decimal", "tk_cadena"} or tok.lexema in {"True", "False", "None"}:
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
        self.reportar_error(tok, esperados=["id", "num", "cadena", "(", "[", "lambda", "True", "False", "None"])

    def lista_argumentos(self):
        # expr inicial
        self.expresion()

        # generador en argumento: expr 'for' id 'in' expr ('if' expr)* ( 'for' ... )*
        if self.act.lexema == "for":
            self.comp_for()
            return

        # lista clásica de argumentos
        while self.act.lexema == ",":
            self.emparejar(",")
            if self.act.lexema == ")":
                break
            self.expresion()
            if self.act.lexema == "for":
                self.comp_for()
                break

        if self.act.lexema not in (")", ","):
            self.reportar_error(self.act, esperados=[")", ","])

    def comp_for(self):
        # ('for' id 'in' expresion ('if' expresion)*)+
        while True:
            self.emparejar("for")
            self.emparejar("id", mostrar=["identificador"])
            self.emparejar("in")
            self.expresion()
            while self.act.lexema == "if":
                self.emparejar("if")
                self.expresion()
            if self.act.lexema != "for":
                break

    def expresion_lambda(self):
        self.emparejar("lambda")
        if self.act.lexema != ":":
            self.parametros_lambda()
        self.emparejar(":", mostrar=[":"])
        self.expresion()

    def parametros_lambda(self):
        self.emparejar("id", mostrar=["identificador"])
        while self.act.lexema == ",":
            self.emparejar(",")
            self.emparejar("id", mostrar=["identificador"])

    
    def imprimir_conjuntos_teoricos(self):
        # Conjuntos FIRST y FOLLOW aproximados y coherentes con las funciones/decisiones del parser.
        # Terminales representados por lexemas o por tipos de token cuando aplica.
        FIRST = {
            "programa": {"def", "if", "while", "for", "pass", "break", "continue", "return",
                         "print", "id", "tk_entero", "tk_decimal", "tk_cadena", "(", "[", "lambda",
                         "True", "False", "None", "+", "-"},
            "sentencia": {"def", "if", "while", "for", "pass", "break", "continue", "return",
                          "print", "id", "tk_entero", "tk_decimal", "tk_cadena", "(", "[", "lambda",
                          "True", "False", "None", "+", "-"},
            "sentencia_simple": {"pass", "break", "continue", "return", "print",
                                 "id", "tk_entero", "tk_decimal", "tk_cadena", "(", "[", "lambda",
                                 "True", "False", "None", "+", "-"},
            "sentencia_expresion": {"id", "tk_entero", "tk_decimal", "tk_cadena", "(", "[", "lambda",
                                    "True", "False", "None", "+", "-"},
            "definicion_funcion": {"def"},
            "sentencia_if": {"if"},
            "sentencia_while": {"while"},
            "sentencia_for": {"for"},
            "bloque": {"def", "if", "while", "for", "pass", "break", "continue", "return",
                       "print", "id", "tk_entero", "tk_decimal", "tk_cadena", "(", "[", "lambda",
                       "True", "False", "None", "+", "-"},
            "parametros": {"id"},
            "parametro": {"id"},
            "tipo_anotado": {"id", "["},
            "lista_expresiones": {"id", "tk_entero", "tk_decimal", "tk_cadena", "(", "[", "lambda",
                                  "True", "False", "None", "+", "-"},
            "expresion": {"id", "tk_entero", "tk_decimal", "tk_cadena", "(", "[", "lambda",
                          "True", "False", "None", "+", "-", "not"},
            "comparacion": {"id", "tk_entero", "tk_decimal", "tk_cadena", "(", "[", "lambda",
                            "True", "False", "None", "+", "-"},
            "expr_arit": {"id", "tk_entero", "tk_decimal", "tk_cadena", "(", "[", "lambda",
                          "True", "False", "None", "+", "-"},
            "termino": {"id", "tk_entero", "tk_decimal", "tk_cadena", "(", "[", "lambda",
                        "True", "False", "None", "+", "-"},
            "factor": {"id", "tk_entero", "tk_decimal", "tk_cadena", "(", "[", "lambda",
                       "True", "False", "None", "+", "-"},
            "potencia": {"id", "tk_entero", "tk_decimal", "tk_cadena", "(", "[", "lambda",
                         "True", "False", "None"},
            "atomo": {"id", "tk_entero", "tk_decimal", "tk_cadena", "(", "[", "lambda",
                      "True", "False", "None"},
            "lista_argumentos": {"id", "tk_entero", "tk_decimal", "tk_cadena", "(", "[", "lambda",
                                 "True", "False", "None", "+", "-", "not"},
            "comp_for": {"for"},
            "expresion_lambda": {"lambda"},
            "parametros_lambda": {"id"},
        }

        # FOLLOW (aprox) útil para entender cierres y separadores
        FOLLOW = {
            "programa": {"EOF"},
            "sentencia": {"def", "if", "while", "for", "pass", "break", "continue", "return",
                          "print", "id", "tk_entero", "tk_decimal", "tk_cadena", "(", "[", "lambda",
                          "True", "False", "None", "+", "-", "EOF"},
            "sentencia_simple": {"def", "if", "while", "for", "pass", "break", "continue", "return",
                                 "print", "id", "tk_entero", "tk_decimal", "tk_cadena", "(", "[",
                                 "lambda", "True", "False", "None", "+", "-", "EOF"},
            "sentencia_expresion": {"def", "if", "while", "for", "pass", "break", "continue", "return",
                                    "print", "id", "tk_entero", "tk_decimal", "tk_cadena", "(", "[",
                                    "lambda", "True", "False", "None", "+", "-", "EOF"},
            "definicion_funcion": {"def", "if", "while", "for", "pass", "break", "continue", "return",
                                   "print", "id", "tk_entero", "tk_decimal", "tk_cadena", "(", "[",
                                   "lambda", "True", "False", "None", "+", "-", "EOF"},
            "sentencia_if": {"def", "if", "while", "for", "pass", "break", "continue", "return",
                             "print", "id", "tk_entero", "tk_decimal", "tk_cadena", "(", "[",
                             "lambda", "True", "False", "None", "+", "-", "EOF"},
            "sentencia_while": {"def", "if", "while", "for", "pass", "break", "continue", "return",
                                "print", "id", "tk_entero", "tk_decimal", "tk_cadena", "(", "[",
                                "lambda", "True", "False", "None", "+", "-", "EOF"},
            "sentencia_for": {"def", "if", "while", "for", "pass", "break", "continue", "return",
                              "print", "id", "tk_entero", "tk_decimal", "tk_cadena", "(", "[",
                              "lambda", "True", "False", "None", "+", "-", "EOF"},
            "bloque": {"def", "if", "while", "for", "else", "elif", "EOF"},
            "parametros": {")"},
            "parametro": {")", ","},
            "tipo_anotado": {")", ",", "]"},
            "lista_expresiones": {")", ",", ":", "]"},
            "expresion": {")", ",", ":", "]", "==", "!=", "<", ">", "<=", ">=", "in", "is",
                          "+", "-", "*", "/", "%", "**"},
            "potencia": {")", ",", ":", "]", "==", "!=", "<", ">", "<=", ">=", "in", "is",
                         "+", "-", "*", "/", "%", "**"},
            "atomo": {"(", "[", ".", ")", ",", ":", "]", "==", "!=", "<", ">", "<=", ">=",
                      "in", "is", "+", "-", "*", "/", "%", "**"},
            "lista_argumentos": {")"},
            "comp_for": {")", ","},
            "expresion_lambda": {")", ",", ":", "]"},
            "parametros_lambda": {":", ","},
        }

        # Conjuntos de PREDICCIÓN por producción (los disparadores que usa tu parser)
        PRED = {
            "sentencia → definicion_funcion": {"def"},
            "sentencia → sentencia_if": {"if"},
            "sentencia → sentencia_while": {"while"},
            "sentencia → sentencia_for": {"for"},
            "sentencia → sentencia_simple": {"pass", "break", "continue", "return", "print",
                                             "id", "tk_entero", "tk_decimal", "tk_cadena",
                                             "(", "[", "lambda", "True", "False", "None", "+", "-"},
            "sentencia_simple → 'return' expresion?": {"return"},
            "sentencia_simple → 'print' '(' arglist? ')'": {"print"},
            "sentencia_simple → 'pass'|'break'|'continue'": {"pass", "break", "continue"},
            "sentencia_simple → sentencia_expresion": {"id", "tk_entero", "tk_decimal", "tk_cadena",
                                                       "(", "[", "lambda", "True", "False", "None", "+", "-"},
            "definicion_funcion → 'def' id '(' parametros? ')' ':' bloque": {"def"},
            "sentencia_if → 'if' expresion ':' bloque ...": {"if"},
            "sentencia_while → 'while' expresion ':' bloque": {"while"},
            "sentencia_for → 'for' id 'in' expresion ':' bloque": {"for"},
            "atomo → id|num|cadena|'('exp')'|'['lista']'|'lambda'": {"id", "tk_entero", "tk_decimal", "tk_cadena",
                                                                     "(", "[", "lambda", "True", "False", "None"},
            "lista_argumentos → expresion (',' expresion)* | expresion comp_for": {
                "id", "tk_entero", "tk_decimal", "tk_cadena", "(", "[", "lambda",
                "True", "False", "None", "+", "-", "not"
            },
            "comp_for → 'for' id 'in' expresion ('if' expresion)* ( 'for' ... )*": {"for"},
        }

        self._emitir("\nCONJUNTOS ")
        self._emitir("PRIMEROS:")
        for nt in sorted(FIRST.keys()):
            self._emitir(f"  PRIMEROS({nt}) = {{{', '.join(sorted(FIRST[nt]))}}}")

        self._emitir("\nSIGUIENTES:")
        for nt in sorted(FOLLOW.keys()):
            self._emitir(f"  SIGUIENTES({nt}) = {{{', '.join(sorted(FOLLOW[nt]))}}}")

        self._emitir("\nPREDICCION")
        for prod in sorted(PRED.keys()):
            self._emitir(f"  PRED({prod}) = {{{', '.join(sorted(PRED[prod]))}}}")
        


# -------------------- función de integración --------------------
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
