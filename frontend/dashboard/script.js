document.addEventListener('DOMContentLoaded', () => {
    // Set date
    const dateEl = document.getElementById('current-date');
    const now = new Date();
    dateEl.textContent = now.toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });

    // Initial Fetch
    fetchRecommendation();
    setInterval(refreshMarketData, 60000);

    // Scenario Buttons
    const scenarioBtns = document.querySelectorAll('.s-btn');
    const scenarioInput = document.getElementById('selected-scenario');
    scenarioBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            scenarioBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            scenarioInput.value = btn.dataset.scenario;
        });
    });

    // Prediction Form Handler
    const form = document.getElementById('prediction-form');
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const data = {
            commodity: document.getElementById('commodity-select').value,
            open: document.getElementById('open-price').value,
            high: document.getElementById('high-price').value,
            volume: document.getElementById('volume-val').value,
            scenario: scenarioInput.value
        };

        try {
            const response = await fetch('/predict', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            const result = await response.json();
            if (result.error) { alert(result.error); return; }

            document.getElementById('prediction-result').classList.remove('hidden');
            document.getElementById('pred-val-1d').innerHTML = `1D: ₹${result.prediction.toLocaleString()}`;
            document.getElementById('pred-val-7d').innerHTML = `7D: ₹${result.forecast_7d.toLocaleString()}`;
            document.getElementById('pred-val-30d').innerHTML = `30D: ₹${result.forecast_30d.toLocaleString()}`;

            // Intelligence Data
            document.getElementById('scenario-explanation').textContent = result.scenario_applied;
            document.getElementById('decision-signal').textContent = `SIGNAL: ${result.decision.signal}`;
            document.getElementById('decision-risk').textContent = `RISK: ${result.decision.risk}`;

            // Simulation Results
            document.getElementById('mc-worst').textContent = `₹${result.monte_carlo.worst.toLocaleString()}`;
            document.getElementById('mc-likely').textContent = `₹${result.monte_carlo.likely.toLocaleString()}`;
            document.getElementById('mc-best').textContent = `₹${result.monte_carlo.best.toLocaleString()}`;

            // XAI Factors
            const xaiList = document.getElementById('xai-list');
            xaiList.innerHTML = result.xai.map(f => `<li><span class="dot"></span> ${f}</li>`).join('');

            renderTrendChart(result);
        } catch (error) { console.error(error); }
    });

    async function refreshMarketData() {
        try {
            const res = await fetch('/prices');
            const data = await res.json();
            document.getElementById('usd-inr-val').textContent = `₹${data.rate}`;
            ['gold', 'silver', 'copper'].forEach(name => {
                const info = data[name];
                if (info.price_inr !== 'N/A') {
                    document.getElementById(`price-${name}-inr`).textContent = `₹${info.price_inr.toLocaleString()}`;
                    document.getElementById(`change-${name}`).textContent = `${info.percent_change}%`;
                    document.getElementById(`change-${name}`).className = `change ${info.percent_change >= 0 ? 'positive' : 'negative'}`;
                }
            });
        } catch (err) { console.error(err); }
    }

    function renderTrendChart(result) {
        const trace = {
            x: ['Present', 'Next-Day', '7-Day', '30-Day'],
            y: [result.current_price, result.prediction, result.forecast_7d, result.forecast_30d],
            type: 'scatter', mode: 'lines+markers',
            line: { color: '#58a6ff', width: 3, shape: 'spline' }
        };
        const layout = {
            title: `${result.commodity} AI Decision Spectrum (₹)`,
            paper_bgcolor: 'rgba(0,0,0,0)', plot_bgcolor: 'rgba(0,0,0,0)',
            font: { color: '#f0f6fc' },
            yaxis: { gridcolor: '#30363d' }, xaxis: { gridcolor: '#30363d' }
        };
        Plotly.newPlot('market-comparison-chart', [trace], layout);
    }

    async function fetchRecommendation() {
        try {
            const res = await fetch('/recommendation');
            const data = await res.json();
            if (data.recommendation) {
                document.getElementById('recommendation-summary').innerHTML =
                    `Best Trend: <strong style="color: #f1c40f;">${data.recommendation.name}</strong> (+${data.recommendation.growth}% momentum)`;
            }
        } catch (err) { console.error(err); }
    }

    // AI Financial Assistant Chatbot Logic
    const chatToggle = document.getElementById('chat-toggle');
    const chatWindow = document.getElementById('chat-window');
    const closeChat = document.getElementById('close-chat');
    const sendBtn = document.getElementById('send-chat');
    const chatInput = document.getElementById('chat-input');
    const chatMessages = document.getElementById('chat-messages');

    chatToggle.addEventListener('click', () => {
        chatWindow.classList.toggle('hidden');
        if (!chatWindow.classList.contains('hidden')) {
            chatInput.focus();
        }
    });

    closeChat.addEventListener('click', () => {
        chatWindow.classList.add('hidden');
    });

    async function sendMessage() {
        const text = chatInput.value.trim();
        if (!text) return;

        // Add user message to UI
        const userMsg = document.createElement('div');
        userMsg.className = 'msg user';
        userMsg.textContent = text;
        chatMessages.appendChild(userMsg);

        chatInput.value = '';
        chatMessages.scrollTop = chatMessages.scrollHeight;

        // Add typing indicator or similar thought if needed
        const botLoadingMsg = document.createElement('div');
        botLoadingMsg.className = 'msg bot';
        botLoadingMsg.textContent = '...';
        chatMessages.appendChild(botLoadingMsg);
        chatMessages.scrollTop = chatMessages.scrollHeight;

        try {
            const res = await fetch('/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: text })
            });
            const data = await res.json();

            // Update loading message with real response
            botLoadingMsg.innerHTML = data.response.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
            chatMessages.scrollTop = chatMessages.scrollHeight;
        } catch (err) {
            console.error('Chat Error:', err);
            botLoadingMsg.textContent = 'I encountered an error. Please try again.';
        }
    }

    sendBtn.addEventListener('click', sendMessage);
    chatInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendMessage();
    });
});
