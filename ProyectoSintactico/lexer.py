import sys

RESERVADAS = {
    "class","def","if","else","elif","while","for","return","print",
    "True","False","None","and","or","not","in","is","break","continue",
    "pass","import","from","as","with","try","except","finally","raise",
    "lambda","yield","global","nonlocal","assert"
}

OPERADORES = {
    "==":"tk_igual_igual",
    "!=":"tk_distinto",
    "<=":"tk_menor_igual",
    ">=":"tk_mayor_igual",
    "->":"tk_flecha",
    "=":"tk_asig",
    "<":"tk_menor",
    ">":"tk_mayor",
    ":":"tk_dos_puntos",
    ",":"tk_coma",
    ".":"tk_punto",
    "(":"tk_par_izq",
    ")":"tk_par_der",
    "{":"tk_llave_izq",
    "}":"tk_llave_der",
    "[":"tk_cor_izq",
    "]":"tk_cor_der",
    "+":"tk_suma",
    "-":"tk_resta",
    "*":"tk_mul",
    "/":"tk_div",
    "%":"tk_mod"
}

def es_letra(ch):
    return ('a' <= ch <= 'z') or ('A' <= ch <= 'Z') or ch == '_'

class Buffer:
    def __init__(self, texto):
        self.texto = texto
        self.i = 0
        self.linea = 1
        self.col = 1

    def eof(self):
        return self.i >= len(self.texto)

    def ver(self, k=0):
        idx = self.i + k
        if idx < len(self.texto):
            return self.texto[idx]
        return ''

    def siguiente(self):
        if self.eof():
            return ''
        ch = self.texto[self.i]
        self.i += 1
        if ch == '\n':
            self.linea += 1
            self.col = 1
        else:
            if ch == '\t':
                self.col += 4  # ancho de tab aproximado
            else:
                self.col += 1
        return ch

    def get_pos(self):
        return self.linea, self.col

class Token:
    def __init__(self, tipo, lexema, linea, col):
        self.tipo = tipo      # p.ej., 'id', 'tk_entero', 'def', 'tk_par_izq'
        self.lexema = lexema  # texto real
        self.linea = linea
        self.col = col

    def __repr__(self):
        return f"Token({self.tipo!r},{self.lexema!r},{self.linea},{self.col})"

class Automata:
    def aceptar(self, buf: Buffer):
        raise NotImplementedError

class AFDIdentificador(Automata):
    def aceptar(self, buf):
        ch = buf.ver()
        if not (es_letra(ch) or ch == '_'):
            return None
        linea_ini, col_ini = buf.get_pos()
        lex = ''
        i = 0
        while not buf.eof() and (es_letra(buf.ver(i)) or buf.ver(i).isdigit() or buf.ver(i) == '_'):
            lex += buf.ver(i)
            i += 1
        tipo = lex if lex in RESERVADAS else "id"
        return (tipo, lex, linea_ini, col_ini, i)

class AFDEntero(Automata):
    def aceptar(self, buf):
        ch = buf.ver()
        i = 0
        lex = ''
        if ch in '+-':
            if buf.ver(1).isdigit():
                lex += ch
                i += 1
            else:
                return None
        if buf.ver(i).isdigit():
            while not buf.eof() and buf.ver(i).isdigit():
                lex += buf.ver(i)
                i += 1
            return ("tk_entero", lex, buf.linea, buf.col, i)
        return None

class AFDCadena(Automata):
    def aceptar(self, buf):
        ch = buf.ver()
        if ch not in {'"', "'"}:
            return None
        linea_ini, col_ini = buf.get_pos()
        delim = ch
        lex = delim
        i = 1
        escapado = False
        while not buf.eof():
            c = buf.ver(i)
            if c == '':
                return None  # EOF antes de cerrar
            lex += c
            if escapado:
                escapado = False
            else:
                if c == '\\':
                    escapado = True
                elif c == delim:
                    return ("tk_cadena", lex, linea_ini, col_ini, i+1)
            i += 1
        return None

class AFDOperador(Automata):
    def aceptar(self, buf):
        ch = buf.ver()
        dos = ch + buf.ver(1)
        if dos in OPERADORES:
            return (OPERADORES[dos], dos, buf.linea, buf.col, 2)
        if ch in OPERADORES:
            return (OPERADORES[ch], ch, buf.linea, buf.col, 1)
        return None

class Scanner:
    def __init__(self, texto):
        self.buf = Buffer(texto)
        self.automatas = [AFDCadena(), AFDOperador(), AFDIdentificador(), AFDEntero()]
        self.tokens = []

    def analizar(self):
        b = self.buf
        while not b.eof():
            ch = b.ver()
            if ch.isspace():
                self._consumir_espacios()
                continue
            if ch == '#':
                self._ignorar_comentario()
                continue
            match = None
            for afd in self.automatas:
                match = afd.aceptar(b)
                if match:
                    tipo, lexema, linea, col, n = match
                    for _ in range(n):
                        b.siguiente()
                    self.tokens.append(Token(tipo, lexema, linea, col))
                    break
            if not match:
                # Error lexico, se trata como token desconocido
                linea, col = b.get_pos()
                raise ErrorLexico(linea, col)
        # token EOF
        if self.tokens:
            ultimo = self.tokens[-1]
            self.tokens.append(Token("EOF", "", ultimo.linea, ultimo.col+1))
        else:
            self.tokens.append(Token("EOF", "", 1, 1))

    def _consumir_espacios(self):
        b = self.buf
        while not b.eof() and b.ver().isspace():
            b.siguiente()

    def _ignorar_comentario(self):
        b = self.buf
        while not b.eof() and b.ver() != '\n':
            b.siguiente()

class ErrorLexico(Exception):
    def __init__(self, linea, col):
        self.linea = linea
        self.col = col
        super().__init__(f">>> Error léxico(linea:{linea},posicion:{col})")
