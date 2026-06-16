const $ = (id) => document.getElementById(id);
    let selectedDebugId = null;

    function valueOrDash(value, digits = null) {
      if (value === null || value === undefined || value === "") return "--";
      if (typeof value === "number" && digits !== null) return value.toFixed(digits);
      return value;
    }

    function classifyHint(type, value) {
      if (value === null || value === undefined) return "等待传感器上传";
      if (type === "heart") {
        if (value >= 80) return "心率相对偏高";
        if (value >= 65) return "心率处于平稳区间";
        return "心率较低，身体较放松";
      }
      if (type === "spo2") return value >= 95 ? "血氧处于正常观察范围" : "血氧偏低，需要关注";
      if (type === "temp") return value > 28 ? "温度偏高，可考虑风扇" : "温度处于舒适范围";
      if (type === "humidity") return value > 65 ? "湿度偏高" : "湿度处于舒适范围";
      if (type === "turnover") return value >= 5 ? "翻身较频繁" : "体动较少";
      return "三轴加速度合成值";
    }

    function stateColor(code) {
      if (code === 0) return "#d17916";
      if (code === 1) return "#246bfe";
      if (code === 2) return "#0f9f9a";
      return "#65717d";
    }

    function numberOrNull(value) {
      if (value === null || value === undefined || value === "") return null;
      const number = Number(value);
      return Number.isFinite(number) ? number : null;
    }

    function formatDuration(totalSeconds) {
      const seconds = Math.max(0, Math.round(Number(totalSeconds) || 0));
      const hours = Math.floor(seconds / 3600);
      const minutes = Math.floor((seconds % 3600) / 60);
      const remainingSeconds = seconds % 60;
      if (hours) return `${hours}小时${minutes}分`;
      if (minutes) return `${minutes}分${remainingSeconds}秒`;
      return `${remainingSeconds}秒`;
    }

    function formatClock(value) {
      const date = value ? new Date(String(value).replace(" ", "T")) : null;
      if (!date || Number.isNaN(date.getTime())) return "--:--";
      return date.toLocaleTimeString("zh-CN", {
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
        hour12: false
      });
    }

    function chartFrame(minValue, maxValue, color) {
      const left = 48;
      const right = 586;
      const top = 12;
      const bottom = 142;
      const lines = [0, 0.5, 1].map((ratio) => {
        const y = top + (bottom - top) * ratio;
        const value = maxValue - (maxValue - minValue) * ratio;
        return `<line class="chart-grid" x1="${left}" y1="${y}" x2="${right}" y2="${y}"></line>
          <text class="chart-axis-text" x="4" y="${y + 3}">${value.toFixed(value < 10 ? 1 : 0)}</text>`;
      }).join("");
      return { left, right, top, bottom, color, markup: lines };
    }

    function renderLineChart(svgId, history, field, options) {
      const svg = $(svgId);
      const points = (history || []).map((item, index) => {
        const sensor = item.sensor_data || {};
        const rawValue = typeof field === "function" ? field(sensor) : sensor[field];
        return { index, value: numberOrNull(rawValue) };
      }).filter((item) => item.value !== null);

      if (points.length < 2) {
        svg.innerHTML = `<text class="chart-empty" x="300" y="85">等待更多采样点</text>`;
        return;
      }

      const values = points.map((item) => item.value);
      let minValue = Math.min(...values);
      let maxValue = Math.max(...values);
      const minSpan = options.minSpan || 1;
      if (maxValue - minValue < minSpan) {
        const center = (maxValue + minValue) / 2;
        minValue = center - minSpan / 2;
        maxValue = center + minSpan / 2;
      } else {
        const padding = (maxValue - minValue) * 0.12;
        minValue -= padding;
        maxValue += padding;
      }
      if (options.floor !== undefined) minValue = Math.min(options.floor, minValue);
      if (options.ceiling !== undefined) maxValue = Math.max(options.ceiling, maxValue);
      if (maxValue <= minValue) maxValue = minValue + minSpan;

      const frame = chartFrame(minValue, maxValue, options.color);
      const denominator = Math.max(1, history.length - 1);
      const path = points.map((point, pointIndex) => {
        const x = frame.left + (point.index / denominator) * (frame.right - frame.left);
        const y = frame.bottom - ((point.value - minValue) / (maxValue - minValue)) * (frame.bottom - frame.top);
        return `${pointIndex ? "L" : "M"} ${x.toFixed(2)} ${y.toFixed(2)}`;
      }).join(" ");
      const firstTime = history[0] && history[0].timestamp;
      const lastTime = history[history.length - 1] && history[history.length - 1].timestamp;

      svg.innerHTML = `${frame.markup}
        <path class="chart-line" stroke="${options.color}" d="${path}"></path>
        <text class="chart-axis-text" x="${frame.left}" y="163">${formatClock(firstTime)}</text>
        <text class="chart-axis-text" x="${frame.right}" y="163" text-anchor="end">${formatClock(lastTime)}</text>`;
    }

    function renderStageChart(history) {
      const svg = $("stageChart");
      const points = (history || []).map((item, index) => {
        const result = item.model_sleep_result || {};
        const code = numberOrNull(result.sleep_state_code);
        const valid = Number(result.state_valid) === 1;
        return { index, code: valid && [0, 1, 2].includes(code) ? code : 0 };
      });

      if (!points.length) {
        svg.innerHTML = `<text class="chart-empty" x="300" y="95">等待睡眠监测数据</text>`;
        return;
      }

      const left = 72;
      const right = 586;
      const stageY = { 0: 24, 1: 84, 2: 144 };
      const labels = [
        { code: 0, text: "未入睡", color: "#d17916" },
        { code: 1, text: "浅睡眠", color: "#246bfe" },
        { code: 2, text: "深度睡眠", color: "#0f9f9a" }
      ];
      const grid = labels.map((item) => `
        <line class="chart-grid" x1="${left}" y1="${stageY[item.code]}" x2="${right}" y2="${stageY[item.code]}"></line>
        <circle cx="7" cy="${stageY[item.code] - 3}" r="4" fill="${item.color}"></circle>
        <text class="chart-axis-text" x="16" y="${stageY[item.code]}">${item.text}</text>
      `).join("");
      const denominator = Math.max(1, history.length - 1);
      let path = "";
      points.forEach((point, index) => {
        const x = points.length === 1
          ? left
          : left + (point.index / denominator) * (right - left);
        const y = stageY[point.code];
        if (index === 0) {
          path = `M ${x.toFixed(2)} ${y}`;
          return;
        }
        path += ` H ${x.toFixed(2)} V ${y}`;
      });
      if (points.length === 1) {
        path += ` H ${right}`;
      }

      svg.innerHTML = `${grid}
        <path class="chart-line" stroke="#53667a" d="${path}"></path>
        <text class="chart-axis-text" x="${left}" y="181">${formatClock(history[0].timestamp)}</text>
        <text class="chart-axis-text" x="${right}" y="181" text-anchor="end">${formatClock(history[history.length - 1].timestamp)}</text>`;
    }

    function buildSleepEvaluation(summary) {
      const stageSeconds = summary.stage_seconds || {};
      const observed = Number(summary.observed_sleep_seconds) || 0;
      const sleeping = Number(summary.sleep_seconds) || 0;
      const deep = Number(stageSeconds["2"] ?? stageSeconds[2]) || 0;
      const sleepRatio = summary.sleep_ratio;
      const averageHeart = numberOrNull(summary.average_heart_rate);
      const averageSpo2 = numberOrNull(summary.average_spo2);
      const lowSpo2Ratio = numberOrNull(summary.spo2_low_ratio);

      if (observed < 30 || summary.sample_count < 15) {
        return {
          score: null,
          label: "数据积累中",
          description: "至少积累 30 秒有效阶段数据后生成初步趋势评价。",
          advice: ["保持设备稳定佩戴并继续监测，以获得更完整的睡眠结构。"]
        };
      }

      let score = 20;
      score += Math.min(40, Math.max(0, Number(sleepRatio || 0) * 40));
      const deepRatio = sleeping ? deep / sleeping : 0;
      score += Math.min(20, deepRatio / 0.2 * 20);

      if (averageSpo2 !== null) {
        score += averageSpo2 >= 95 ? 15 : Math.max(0, (averageSpo2 - 88) / 7 * 15);
      }
      if (averageHeart !== null) {
        score += averageHeart >= 45 && averageHeart <= 80 ? 5 : 2;
      }
      if (lowSpo2Ratio !== null) score -= Math.min(15, lowSpo2Ratio * 60);
      score = Math.round(Math.min(100, Math.max(0, score)));

      let label = "睡眠状态一般";
      let description = "当前睡眠结构仍有改善空间，建议结合整夜趋势持续观察。";
      if (score >= 85) {
        label = "睡眠状态良好";
        description = "当前阶段结构和主要体征整体平稳。";
      } else if (score >= 70) {
        label = "睡眠状态尚可";
        description = "整体表现尚可，个别指标可继续关注。";
      } else if (score < 55) {
        label = "建议重点关注";
        description = "当前睡眠连续性或体征指标存在较明显波动。";
      }

      const advice = [];
      if (sleepRatio !== null && sleepRatio < 0.75) {
        advice.push("未入睡时间占比较高，建议固定入睡时间并减少睡前强光和电子设备使用。");
      }
      if (sleeping >= 30 * 60 && deepRatio < 0.12) {
        advice.push("深睡占比较低，可尝试保持规律运动，并避免临睡前摄入咖啡因。");
      }
      if (averageSpo2 !== null && (averageSpo2 < 95 || (lowSpo2Ratio || 0) > 0.05)) {
        advice.push("监测到血氧偏低趋势，请检查传感器佩戴；若反复出现或伴随不适，建议咨询医生。");
      }
      if (averageHeart !== null && averageHeart > 80) {
        advice.push("睡眠期平均心率偏高，建议避免睡前剧烈运动、酒精和过量进食。");
      }
      const averageTemperature = numberOrNull(summary.average_temperature);
      const averageHumidity = numberOrNull(summary.average_humidity);
      if (averageTemperature !== null && (averageTemperature < 18 || averageTemperature > 26)) {
        advice.push("睡眠环境温度偏离舒适区间，可将室温调整到约 18–26°C。");
      }
      if (averageHumidity !== null && (averageHumidity < 40 || averageHumidity > 65)) {
        advice.push("环境湿度不够理想，建议尽量维持在 40%–65%。");
      }
      if (!advice.length) {
        advice.push("当前主要指标较平稳，继续保持规律作息并完成整夜监测。");
      }

      return { score, label, description, advice };
    }

    function renderAnalysis(history, summary) {
      renderLineChart("heartChart", history, "heart_rate_bpm", {
        color: "#d84a4a", minSpan: 12
      });
      renderLineChart("spo2Chart", history, "spo2_percent", {
        color: "#246bfe", minSpan: 4, floor: 90, ceiling: 100
      });
      renderLineChart("temperatureChart", history, "temperature_c", {
        color: "#d17916", minSpan: 4
      });
      renderLineChart("humidityChart", history, "humidity_percent", {
        color: "#0f9f9a", minSpan: 10
      });
      renderLineChart("accelChart", history, (sensor) => {
        const ax = numberOrNull(sensor.accel_x);
        const ay = numberOrNull(sensor.accel_y);
        const az = numberOrNull(sensor.accel_z);
        if ([ax, ay, az].some((value) => value === null)) return null;
        return Math.sqrt(ax * ax + ay * ay + az * az);
      }, {
        color: "#7c5ce0", minSpan: 0.15, floor: 0
      });
      renderLineChart("turnoverChart", history, "turnover_count", {
        color: "#53667a", minSpan: 2, floor: 0
      });
      renderStageChart(history);

      const stageSeconds = summary.stage_seconds || {};
      const observed = Number(summary.observed_sleep_seconds) || 0;
      const stages = [
        { code: 0, name: "未入睡", color: "#d17916" },
        { code: 1, name: "浅睡眠", color: "#246bfe" },
        { code: 2, name: "深度睡眠", color: "#0f9f9a" }
      ].map((stage) => {
        const seconds = Number(stageSeconds[String(stage.code)] ?? stageSeconds[stage.code]) || 0;
        const percent = observed ? seconds / observed * 100 : 0;
        return { ...stage, seconds, percent };
      });
      const segments = stages.map((stage) => `
        <div class="duration-segment"
          title="${stage.name} ${formatDuration(stage.seconds)}"
          style="width:${stage.percent.toFixed(2)}%;background:${stage.color}">
        </div>
      `).join("");
      const details = stages.map((stage) => `
        <div class="duration-detail">
          <span class="duration-name"><span class="stage-dot" style="background:${stage.color}"></span>${stage.name}</span>
          <strong class="duration-value">${formatDuration(stage.seconds)}</strong>
          <span class="duration-percent">${stage.percent.toFixed(1)}%</span>
        </div>
      `).join("");
      $("durationList").innerHTML = `
        <div class="duration-track">${segments}</div>
        <div class="duration-details">${details}</div>
      `;

      const evaluation = buildSleepEvaluation(summary);
      const score = evaluation.score;
      $("sleepScore").innerHTML = `${score === null ? "--" : score}<small>分</small>`;
      $("scoreLabel").textContent = evaluation.label;
      $("scoreDescription").textContent = evaluation.description;
      const scoreDegrees = score === null ? 0 : score * 3.6;
      $("scoreRing").style.background = `conic-gradient(var(--brand) 0deg, var(--brand) ${scoreDegrees}deg, #e7edf3 ${scoreDegrees}deg)`;

      const averageHeart = numberOrNull(summary.average_heart_rate);
      const averageSpo2 = numberOrNull(summary.average_spo2);
      $("averageHeart").textContent = averageHeart === null ? "--" : `${averageHeart.toFixed(1)} bpm`;
      $("averageSpo2").textContent = averageSpo2 === null ? "--" : `${averageSpo2.toFixed(1)}%`;
      $("sleepRatio").textContent = summary.sleep_ratio === null || summary.sleep_ratio === undefined
        ? "--"
        : `${(Number(summary.sleep_ratio) * 100).toFixed(1)}%`;
      $("observedTime").textContent = formatDuration(observed);
      $("adviceList").innerHTML = evaluation.advice.map((item) => `<li>${escapeHtml(item)}</li>`).join("");

      if (summary.started_at && summary.last_sample_at) {
        $("analysisRange").textContent = `${formatClock(summary.started_at)} - ${formatClock(summary.last_sample_at)}`;
      } else {
        $("analysisRange").textContent = "等待有效睡眠数据";
      }
    }

    function escapeHtml(value) {
      return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#39;");
    }

    function renderDebug(history) {
      const records = history || [];

      if (!records.length) {
        selectedDebugId = null;
        $("debugList").innerHTML = `<div class="debug-empty">暂无数据</div>`;
        $("debugDetail").textContent = "暂无调试信息";
        return;
      }

      if (!records.some((item) => item.id === selectedDebugId)) {
        selectedDebugId = records[records.length - 1].id;
      }

      $("debugList").innerHTML = records.slice().reverse().map((item) => {
        const active = item.id === selectedDebugId ? " active" : "";
        const sample = item.sample_id === null || item.sample_id === undefined ? "--" : item.sample_id;
        return `<button class="debug-item${active}" data-id="${item.id}">
          <strong>${escapeHtml(item.timestamp || "未知时间")}</strong>
          <span>sample_id: ${escapeHtml(sample)}</span>
        </button>`;
      }).join("");

      document.querySelectorAll(".debug-item").forEach((button) => {
        button.addEventListener("click", () => {
          selectedDebugId = Number(button.dataset.id);
          renderDebug(records);
        });
      });

      const selected = records.find((item) => item.id === selectedDebugId) || records[records.length - 1];
      $("debugDetail").textContent = JSON.stringify(selected, null, 2);
    }

    function render(data) {
      $("connDot").classList.toggle("connected", Boolean(data.connected));
      $("connText").textContent = data.connected ? `硬件已连接 ${data.client_addr || ""}` : "等待硬件连接";
      $("lastUpdate").textContent = data.last_update_at ? `最近采样 ${data.last_update_at}` : "暂无采样";

      const manualMode = data.control_mode === "manual";
      $("modeSwitch").checked = manualMode;
      $("autoLabel").classList.toggle("active", !manualMode);
      $("manualLabel").classList.toggle("active", manualMode);
      $("modeHint").textContent = manualMode
        ? `手动控制：${data.manual_control_label || "空调 26°C"}`
        : "按睡眠状态和环境自动调节";

      const sensor = data.sensor || {};
      const result = data.result || {};
      const code = result.sleep_state_code;
      const stateName = result.sleep_state_name || "等待数据";

      $("sleepState").textContent = stateName;
      $("stateBadge").textContent = code === undefined || code === null ? "--" : code;
      $("stateBadge").style.background = stateColor(code);

      $("heartRate").textContent = valueOrDash(sensor.heart_rate_bpm);
      $("spo2").textContent = valueOrDash(sensor.spo2_percent);
      $("temperature").textContent = valueOrDash(sensor.temperature_c);
      $("humidity").textContent = valueOrDash(sensor.humidity_percent);
      $("turnover").textContent = valueOrDash(sensor.turnover_count);

      const ax = Number(sensor.accel_x || 0);
      const ay = Number(sensor.accel_y || 0);
      const az = Number(sensor.accel_z || 0);
      const accelMagnitude = sensor.accel_x === undefined ? null : Math.sqrt(ax * ax + ay * ay + az * az);
      $("accel").textContent = valueOrDash(accelMagnitude, 2);

      $("heartHint").textContent = classifyHint("heart", sensor.heart_rate_bpm);
      $("spo2Hint").textContent = classifyHint("spo2", sensor.spo2_percent);
      $("tempHint").textContent = classifyHint("temp", sensor.temperature_c);
      $("humidityHint").textContent = classifyHint("humidity", sensor.humidity_percent);
      $("turnoverHint").textContent = classifyHint("turnover", sensor.turnover_count);
      $("accelHint").textContent = accelMagnitude === null ? "等待传感器上传" : `x=${valueOrDash(sensor.accel_x)} y=${valueOrDash(sensor.accel_y)} z=${valueOrDash(sensor.accel_z)}`;
      const dataHistory = data.data_history || [];
      renderDebug(dataHistory);
      renderAnalysis(data.trend_history || dataHistory, data.session_summary || {});

      document.querySelectorAll(".control-btn").forEach((button) => {
        button.disabled = !manualMode;
        button.classList.toggle("active", button.dataset.command === data.manual_control_key);
      });

      const history = data.control_history || [];
      $("historyList").innerHTML = history.length
        ? history.slice().reverse().map((item) => {
            const ok = item.send_status === "applied" || item.send_status === "sent";
            const pending = item.send_status === "pending";
            const skipped = item.send_status === "skipped" || item.send_status === "no_action";
            const label = ok ? "已执行" : pending ? "待下发" : skipped ? "跳过/无动作" : "异常";
            return `<div class="history-item">
              <span><strong>${item.command_name || item.command_key}</strong>${item.timestamp || ""}</span>
              <span class="${ok ? "sent" : "failed"}">${label}</span>
            </div>`;
          }).join("")
        : `<div class="history-item"><span>暂无控制记录</span><span>--</span></div>`;
    }

    async function loadState() {
      const res = await fetch("/api/state");
      render(await res.json());
    }

    async function sendControl(command) {
      const res = await fetch("/api/control", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ command })
      });
      const body = await res.json();
      if (body.state) render(body.state);
    }

    async function setMode(mode) {
      const res = await fetch("/api/mode", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mode })
      });
      const body = await res.json();
      if (body.state) render(body.state);
    }

    document.querySelectorAll(".control-btn").forEach((button) => {
      button.addEventListener("click", () => sendControl(button.dataset.command));
    });

    $("modeSwitch").addEventListener("change", (event) => {
      setMode(event.target.checked ? "manual" : "auto");
    });

    $("debugSwitch").addEventListener("change", (event) => {
      $("debugPanel").classList.toggle("open", event.target.checked);
    });

    const events = new EventSource("/events");
    events.onmessage = (event) => render(JSON.parse(event.data));
    events.onerror = () => setTimeout(loadState, 1200);
    loadState();
