$colors = @("Red", "DarkYellow", "Yellow", "Green", "Blue", "DarkMagenta", "Magenta")
$text = "Running main.py"

for ($i = 0; $i -lt $text.Length; $i++) {
    Write-Host -NoNewline $text[$i] -ForegroundColor $colors[$i % $colors.Length]
}
Write-Host ""
