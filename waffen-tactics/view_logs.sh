#!/bin/bash
# View Waffen Tactics Bot logs

echo "🔍 Waffen Tactics Bot Log Viewer"
echo "================================="
echo ""

show_menu() {
    echo "1) Ostatnie 50 linii wszystkich logów"
    echo "2) Ostatnie 50 linii błędów"
    echo "3) Szukaj po user_id"
    echo "4) Szukaj po słowie kluczowym"
    echo "5) Pokaż logi przenoszenia jednostek (MOVE)"
    echo "6) Pokaż wszystkie WARNING i ERROR"
    echo "7) Live tail wszystkich logów"
    echo "8) Live tail tylko błędów"
    echo "9) Wyświetl rozmiary plików logów"
    echo "0) Wyczyść stare logi (backup)"
    echo "q) Wyjście"
    echo ""
    read -p "Wybierz opcję: " choice
}

while true; do
    show_menu
    
    case $choice in
        1)
            echo "📋 Ostatnie 50 linii:"
            tail -50 bot.log
            echo ""
            read -p "Naciśnij Enter..."
            ;;
        2)
            echo "❌ Ostatnie błędy:"
            if [ -s bot_errors.log ]; then
                tail -50 bot_errors.log
            else
                echo "Brak błędów!"
            fi
            echo ""
            read -p "Naciśnij Enter..."
            ;;
        3)
            read -p "Podaj user_id: " user_id
            echo "🔎 Szukam logów dla user_id: $user_id"
            grep "$user_id" bot.log | tail -50
            echo ""
            read -p "Naciśnij Enter..."
            ;;
        4)
            read -p "Podaj słowo kluczowe: " keyword
            echo "🔎 Szukam: $keyword"
            grep -i "$keyword" bot.log | tail -50
            echo ""
            read -p "Naciśnij Enter..."
            ;;
        5)
            echo "📦 Logi przenoszenia jednostek:"
            grep -E "\[MOVE_|SELECT_UNIT" bot.log | tail -50
            echo ""
            read -p "Naciśnij Enter..."
            ;;
        6)
            echo "⚠️ Wszystkie ostrzeżenia i błędy:"
            grep -E "\[WARNING\]|\[ERROR\]" bot.log | tail -50
            echo ""
            read -p "Naciśnij Enter..."
            ;;
        7)
            echo "📡 Live tail (Ctrl+C aby zatrzymać)..."
            tail -f bot.log
            ;;
        8)
            echo "📡 Live tail błędów (Ctrl+C aby zatrzymać)..."
            tail -f bot_errors.log
            ;;
        9)
            echo "📊 Rozmiary plików:"
            ls -lh bot*.log* 2>/dev/null
            echo ""
            echo "Rotacja: maksymalnie 10MB, 5 backupów"
            echo ""
            read -p "Naciśnij Enter..."
            ;;
        0)
            echo "🗑️ Tworzenie backupu i czyszczenie..."
            timestamp=$(date +%Y%m%d_%H%M%S)
            if [ -s bot.log ]; then
                mv bot.log "bot_backup_${timestamp}.log"
                echo "✅ Backup: bot_backup_${timestamp}.log"
            fi
            if [ -s bot_errors.log ]; then
                mv bot_errors.log "bot_errors_backup_${timestamp}.log"
                echo "✅ Backup: bot_errors_backup_${timestamp}.log"
            fi
            # Bot automatically creates new files
            echo "✅ Stare logi zarchiwizowane!"
            echo ""
            read -p "Naciśnij Enter..."
            ;;
        q|Q)
            echo "👋 Do zobaczenia!"
            exit 0
            ;;
        *)
            echo "❌ Nieprawidłowa opcja!"
            sleep 1
            ;;
    esac
    
    clear
done
