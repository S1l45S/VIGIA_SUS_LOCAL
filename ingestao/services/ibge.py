def digito_verificador(codigo6):
    """Calcula o dígito verificador de um código IBGE de 6 dígitos.

    Pesos 1, 2, 1, 2, 1, 2. Os algarismos de cada produto são somados e o
    dígito eh o complemento da soma para a próxima dezena.
    """
    texto = str(codigo6).strip()
    if not texto.isdigit() or len(texto) != 6:
        raise ValueError("O código de 6 dígitos deve ter apenas números.")
    soma = 0
    for posicao, algarismo in enumerate(texto):
        produto = int(algarismo) * (1 if posicao % 2 == 0 else 2)
        soma += produto // 10 + produto % 10
    return (10 - soma % 10) % 10


def com_dv(codigo):
    """Devolve o código de 7 dígitos

    Aceita 6 dígitos, que ganham o dígito verificador, ou 7 digitos, que têm
    o dígito conferido
    """
    texto = str(codigo).strip()
    if not texto.isdigit():
        raise ValueError("O código de município deve ter apenas números.")
    if len(texto) == 6:
        return texto + str(digito_verificador(texto))
    if len(texto) == 7:
        if int(texto[6]) != digito_verificador(texto[:6]):
            raise ValueError(f"Dígito verificador inválido: {texto}.")
        return texto
    raise ValueError("O código de município deve ter 6 ou 7 dígitos.")