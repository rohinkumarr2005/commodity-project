/* ═══════════════════════════════════════════════════════════
   Commodity Intelligence — Frontend Controller (app.js)
   Member 1: Prediction + Explainable AI
   ═══════════════════════════════════════════════════════════ */

document.addEventListener("DOMContentLoaded", () => {

    // ── DOM refs ─────────────────────────────────────────
    const selector   = document.getElementById("commoditySelector");
    const loader     = document.getElementById("loader");
    const errorPanel = document.getElementById("errorPanel");
    const errorMsg   = document.getElementById("errorMsg");
    const colLeft    = document.getElementById("colLeft");
    const colRight   = document.getElementById("colRight");

    // overview
    const commodityName = document.getElementById("commodityName");
    const tickerBadge   = document.getElementById("tickerBadge");
    const dateLabel     = document.getElementById("dateLabel");
    const spotPrice     = document.getElementById("spotPrice");
    const unitLabel     = document.getElementById("unitLabel");

    // predictions
    const p1Card  = document.getElementById("p1Card"),  p1Price = document.getElementById("p1Price"),  p1Badge = document.getElementById("p1Badge");
    const p7Card  = document.getElementById("p7Card"),  p7Price = document.getElementById("p7Price"),  p7Badge = document.getElementById("p7Badge");
    const p30Card = document.getElementById("p30Card"), p30Price= document.getElementById("p30Price"), p30Badge= document.getElementById("p30Badge");

    // xai
    const xaiSummary = document.getElementById("xaiSummary");
    const trendVal   = document.getElementById("trendVal"),  trendFill = document.getElementById("trendFill");
    const volVal     = document.getElementById("volVal"),    volFill   = document.getElementById("volFill");
    const volaVal    = document.getElementById("volaVal"),   volaFill  = document.getElementById("volaFill");
    const coefList   = document.getElementById("coefList");

    let chart = null;

    // commodity accent colours
    const ACCENTS = {
        gold:   { line: "#F5A623", glow: "rgba(245,166,35,0.25)", chipClass: "active-gold"   },
        silver: { line: "#C0C0C0", glow: "rgba(192,192,192,0.25)", chipClass: "active-silver" },
        copper: { line: "#B87333", glow: "rgba(184,115,51,0.25)", chipClass: "active-copper" },
    };

    // ── Boot ─────────────────────────────────────────────
    loadCommodity("gold");

    // ── Chip clicks ──────────────────────────────────────
    selector.addEventListener("click", e => {
        const chip = e.target.closest(".commodity-chip");
        if (!chip) return;
        const key = chip.dataset.key;
        // clear active states
        selector.querySelectorAll(".commodity-chip").forEach(c => {
            c.className = "commodity-chip";
        });
        chip.classList.add(ACCENTS[key]?.chipClass || "active-gold");
        loadCommodity(key);
    });

    // ── Fetch + Render ───────────────────────────────────
    async function loadCommodity(key) {
        loader.style.display  = "flex";
        errorPanel.style.display = "none";
        colLeft.style.display = "none";
        colRight.style.display= "none";

        try {
            const res  = await fetch(`/api/predict?commodity=${key}`);
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || "Server error");
            render(data, key);
        } catch (err) {
            loader.style.display = "none";
            errorMsg.textContent = err.message;
            errorPanel.style.display = "flex";
        }
    }

    function render(d, key) {
        loader.style.display  = "none";
        colLeft.style.display = "flex";
        colRight.style.display= "flex";

        const accent = ACCENTS[key] || ACCENTS.gold;

        // overview
        commodityName.childNodes[0].textContent = d.commodity_name + " ";
        tickerBadge.textContent = d.ticker;
        dateLabel.textContent   = `As of ${d.latest_date} · ${d.unit}`;
        spotPrice.textContent   = "$" + d.current_price.toLocaleString("en-US", {minimumFractionDigits:2});
        unitLabel.textContent   = d.unit;

        // predictions
        fillPred(p1Card, p1Price, p1Badge, d.predictions["1"]);
        fillPred(p7Card, p7Price, p7Badge, d.predictions["7"]);
        fillPred(p30Card,p30Price,p30Badge,d.predictions["30"]);

        // xai summary
        xaiSummary.innerHTML = `<i class="fa-solid fa-quote-left" style="color:var(--gold);margin-right:.45rem"></i>${d.xai.summary}`;

        // meters
        setMeter(trendVal, trendFill, d.xai.trend.state,
            `${d.xai.trend.state} (${d.xai.trend.difference_pct>=0?"+":""}${d.xai.trend.difference_pct.toFixed(1)}%)`,
            Math.min(Math.max((d.xai.trend.difference_pct+10)*5,10),100));

        const vc = d.xai.volume;
        const vcClass = vc.state==="UP"?"bullish":vc.state==="DOWN"?"bearish":"neutral";
        setMeter(volVal, volFill, vc.state,
            `${vc.state} (${vc.ratio.toFixed(2)}x)`,
            Math.min(Math.max(vc.ratio*50,10),100), vcClass);

        const vl = d.xai.volatility;
        const vlClass = vl.state==="LOW"?"bullish":vl.state==="HIGH"?"bearish":"neutral";
        setMeter(volaVal, volaFill, vl.state,
            `${vl.state} (${(vl.current*100).toFixed(2)}% dev)`,
            Math.min(Math.max((vl.current/(vl.average+1e-8))*50,10),100), vlClass);

        // coefficients
        coefList.innerHTML = "";
        d.xai.factors.forEach(f => {
            const bull = f.prediction_contribution >= 0;
            coefList.insertAdjacentHTML("beforeend", `
                <div class="coef-item">
                    <div class="coef-left">
                        <span class="coef-dot ${bull?"bullish":"bearish"}"></span>
                        <span class="coef-name">${f.name}</span>
                    </div>
                    <div class="coef-right">
                        <div class="coef-val ${bull?"bullish":"bearish"}">${bull?"+":""}${f.prediction_contribution.toFixed(4)}</div>
                        <div class="coef-sub">scaled contribution</div>
                    </div>
                </div>`);
        });

        // chart
        drawChart(d, accent);
    }

    // ── Helpers ───────────────────────────────────────────
    function fillPred(card, priceEl, badgeEl, p) {
        card.className = `pred-card ${p.direction==="UP"?"bullish":"bearish"}`;
        priceEl.textContent = "$" + p.predicted_price.toLocaleString("en-US", {minimumFractionDigits:2});
        if (p.direction === "UP") {
            badgeEl.className = "pred-badge up";
            badgeEl.innerHTML = `<i class="fa-solid fa-arrow-trend-up"></i> +${p.percent_change.toFixed(1)}%`;
        } else {
            badgeEl.className = "pred-badge down";
            badgeEl.innerHTML = `<i class="fa-solid fa-arrow-trend-down"></i> ${p.percent_change.toFixed(1)}%`;
        }
    }

    function setMeter(valEl, fillEl, state, text, pct, forceClass) {
        const cls = forceClass || (state==="UP"?"bullish":state==="DOWN"?"bearish":"neutral");
        valEl.textContent = text;
        valEl.className   = `meter-value ${cls}`;
        fillEl.className  = `meter-fill ${cls}`;
        fillEl.style.width= `${pct}%`;
    }

    // ── Chart.js ─────────────────────────────────────────
    function drawChart(d, accent) {
        const ctx = document.getElementById("mainChart").getContext("2d");
        if (chart) chart.destroy();

        const hist   = d.history;
        const labels = hist.map(h => h.date);
        const prices = hist.map(h => h.price);

        const lastDate = new Date(d.latest_date);
        const addD = (dt, n) => { const r=new Date(dt); r.setDate(r.getDate()+n); return r.toISOString().split("T")[0]; };
        labels.push(addD(lastDate,1), addD(lastDate,7), addD(lastDate,30));

        const histData = [...prices, null, null, null];

        const foreData = Array(prices.length).fill(null);
        foreData[prices.length-1] = d.current_price;
        foreData.push(d.predictions["1"].predicted_price, d.predictions["7"].predicted_price, d.predictions["30"].predicted_price);

        const grad = ctx.createLinearGradient(0,0,0,350);
        grad.addColorStop(0, accent.glow);
        grad.addColorStop(1, "rgba(0,0,0,0)");

        const isUp = d.predictions["1"].direction === "UP";
        const predColor = isUp ? "#10B981" : "#F43F5E";

        chart = new Chart(ctx, {
            type: "line",
            data: {
                labels,
                datasets: [
                    {
                        label: "Historical Price",
                        data: histData,
                        borderColor: accent.line,
                        borderWidth: 3,
                        pointBackgroundColor: accent.line,
                        pointBorderColor: "#070A0F",
                        pointHoverRadius: 6,
                        fill: true,
                        backgroundColor: grad,
                        tension: .15,
                    },
                    {
                        label: "Projected Curve",
                        data: foreData,
                        borderColor: predColor,
                        borderWidth: 3,
                        borderDash: [6,4],
                        pointBackgroundColor: predColor,
                        pointBorderColor: "#070A0F",
                        pointRadius: [...Array(prices.length-1).fill(0), 4, 7, 7, 7],
                        pointHoverRadius: 8,
                        fill: false,
                        tension: .15,
                    },
                ],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: "top",
                        labels: { color: "#94A3B8", font: { family: "Inter", size: 12, weight: "500" } },
                    },
                    tooltip: {
                        backgroundColor: "#161C26",
                        titleColor: "#F1F5F9",
                        bodyColor: "#F1F5F9",
                        borderColor: "rgba(255,255,255,.08)",
                        borderWidth: 1,
                        padding: 12,
                        cornerRadius: 8,
                        displayColors: false,
                        callbacks: {
                            label: ctx => {
                                let l = ctx.dataset.label || "";
                                if (ctx.parsed.y !== null)
                                    l += ": " + new Intl.NumberFormat("en-US",{style:"currency",currency:"USD"}).format(ctx.parsed.y);
                                return l;
                            },
                        },
                    },
                },
                scales: {
                    x: {
                        grid: { color: "rgba(255,255,255,.03)", drawBorder: false },
                        ticks: { color: "#94A3B8", font: { family: "Inter", size: 10 }, maxTicksLimit: 12 },
                    },
                    y: {
                        grid: { color: "rgba(255,255,255,.03)", drawBorder: false },
                        ticks: { color: "#94A3B8", font: { family: "Inter", size: 10 }, callback: v => "$"+v },
                    },
                },
            },
        });
    }
});
