"""Ponto de entrada da aplicação — executa em HTTPS local em 127.0.0.1:5000."""
import os
import ssl

from app import create_app

app = create_app()

if __name__ == '__main__':
    BASE_DIR = os.path.dirname(__file__)
    cert_file = os.path.join(BASE_DIR, 'certs', 'cert.pem')
    key_file = os.path.join(BASE_DIR, 'certs', 'key.pem')

    if not os.path.exists(cert_file) or not os.path.exists(key_file):
        print()
        print('  ERRO: Certificado SSL não encontrado.')
        print('  Execute setup.bat primeiro.')
        print()
        exit(1)

    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(cert_file, key_file)

    # Backup automático a cada inicialização (snapshot consistente + rotação).
    # Nunca impede o app de subir se algo falhar.
    try:
        from backup import fazer_backup
        destino = fazer_backup()
        if destino:
            print(f'  [backup] snapshot criado: {os.path.basename(destino)}')
    except Exception as e:  # pragma: no cover
        print(f'  [backup] aviso: falha ao gerar snapshot ({e})')

    print()
    print('  ========================================')
    print('       Gastos Pessoais - Local')
    print('  ========================================')
    print('  Acesse: https://127.0.0.1:5000')
    print('  Pressione Ctrl+C para parar')
    print('  ========================================')
    print()

    app.run(
        host='127.0.0.1',
        port=5000,
        ssl_context=context,
        debug=False,
    )
