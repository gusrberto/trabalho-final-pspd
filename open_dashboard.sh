#!/bin/bash

echo "🚀 Abrindo o Dashboard do Game of Life..."
echo "📊 URL: http://localhost:8080"
echo ""

# Verificar se o port forwarding está ativo
if ! pgrep -f "port-forward.*metrics-dashboard" > /dev/null; then
    echo "⚠️  Port forwarding não está ativo. Iniciando..."
    kubectl port-forward -n dashboard deployment/metrics-dashboard 8080:8080 &
    sleep 3
fi

# Verificar se o dashboard está respondendo
if curl -s http://localhost:8080 > /dev/null; then
    echo "✅ Dashboard está funcionando!"
    echo "🌐 Abrindo no navegador..."
    
    # Tentar abrir no navegador padrão
    if command -v xdg-open > /dev/null; then
        xdg-open http://localhost:8080
    elif command -v open > /dev/null; then
        open http://localhost:8080
    else
        echo "📋 Copie e cole esta URL no seu navegador:"
        echo "   http://localhost:8080"
    fi
else
    echo "❌ Dashboard não está respondendo. Verificando status..."
    kubectl get pods -n dashboard
    echo ""
    echo "🔄 Tentando reiniciar o port forwarding..."
    pkill -f "port-forward.*metrics-dashboard"
    kubectl port-forward -n dashboard deployment/metrics-dashboard 8080:8080 &
    sleep 5
    echo "📋 Tente acessar: http://localhost:8080"
fi

echo ""
echo "💡 Dica: Use Ctrl+C para parar este script" 