#!/bin/bash

echo "🧪 Testando Sistema Completo do Game of Life"
echo "=============================================="

# Verificar se os port forwards estão ativos
echo "📡 Verificando port forwarding..."

# Testar Socket Server
echo "🔌 Testando Socket Server..."
if echo "3,4" | nc -w 5 localhost 5000 > /dev/null 2>&1; then
    echo "✅ Socket Server funcionando"
else
    echo "❌ Socket Server não responde"
fi

# Testar ElasticSearch
echo "🔍 Testando ElasticSearch..."
if curl -s http://localhost:9200/_cluster/health > /dev/null 2>&1; then
    echo "✅ ElasticSearch funcionando"
else
    echo "❌ ElasticSearch não responde"
fi

# Testar Dashboard
echo "📊 Testando Dashboard..."
if curl -s http://localhost:8080 > /dev/null 2>&1; then
    echo "✅ Dashboard funcionando"
else
    echo "❌ Dashboard não responde"
fi

# Testar Game of Life completo
echo "🎮 Testando Game of Life..."
RESPONSE=$(echo "3,4" | nc -w 10 localhost 5000)
if echo "$RESPONSE" | grep -q "SUCESSO"; then
    echo "✅ Game of Life funcionando"
    echo "📋 Resposta:"
    echo "$RESPONSE" | head -5
else
    echo "❌ Game of Life falhou"
fi

echo ""
echo "🌐 URLs de Acesso:"
echo "   Socket Server: localhost:5000"
echo "   ElasticSearch: http://localhost:9200"
echo "   Dashboard: http://localhost:8080"
echo ""
echo "📝 Comandos úteis:"
echo "   Testar Game of Life: echo '3,4' | nc localhost 5000"
echo "   Verificar ElasticSearch: curl http://localhost:9200/_cluster/health"
echo "   Abrir Dashboard: xdg-open http://localhost:8080" 