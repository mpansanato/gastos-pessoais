# Hook: auto-commit ao final de sessao Claude Code
# Commita e envia para o GitHub apenas quando houver alteracoes

$projeto = "C:\Users\mpans\OneDrive\Documentos\GitHub\gastos-pessoais"
Set-Location $projeto

# Verifica se ha arquivos modificados
$status = git status --porcelain
if (-not $status) {
    Write-Host "[hook] Nenhuma alteracao encontrada. Nada a commitar."
    exit 0
}

# Protecao: garante que .env nao sera enviado
git rm --cached .env --ignore-unmatch 2>$null
git rm --cached -r instance/ --ignore-unmatch 2>$null
git rm --cached -r certs/ --ignore-unmatch 2>$null

# Adiciona todos os arquivos (respeitando .gitignore)
git add .

# Verifica se .env ou chaves acabaram sendo staged (protecao dupla)
$staged = git diff --cached --name-only
$arquivosProibidos = @(".env", "*.pem", "*.key", "instance/")
foreach ($proibido in $arquivosProibidos) {
    if ($staged -like "*$proibido*") {
        Write-Host "[hook] ATENCAO: $proibido detectado no stage. Removendo..."
        git rm --cached $proibido --ignore-unmatch 2>$null
    }
}

# Gera mensagem de commit baseada no que mudou
$diffStat = git diff --cached --stat
$arquivosAlterados = git diff --cached --name-only

$numArquivos = ($arquivosAlterados | Measure-Object).Count
$lista = ($arquivosAlterados | Select-Object -First 5) -join ", "
if ($numArquivos -gt 5) { $lista += " e mais $($numArquivos - 5) arquivo(s)" }

$data = Get-Date -Format "dd/MM/yyyy HH:mm"
$mensagem = "auto($data): $numArquivos arquivo(s) alterado(s) — $lista"

# Commit
git commit -m $mensagem
if ($LASTEXITCODE -ne 0) {
    Write-Host "[hook] Erro no commit. Verifique os arquivos staged."
    exit 1
}

# Push para o GitHub
git push origin main
if ($LASTEXITCODE -ne 0) {
    Write-Host "[hook] Erro no push. Verifique sua conexao ou credenciais."
    exit 1
}

Write-Host "[hook] ✅ Commit e push realizados com sucesso!"
Write-Host "[hook] Mensagem: $mensagem"
