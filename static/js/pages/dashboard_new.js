import { updateUnreadCount } from '/static/js/pages/announcement.js';

const { createApp, ref, reactive, onMounted } = Vue;

function initEChart(id) {
  const el = document.getElementById(id);
  if (!el) return null;
  return echarts.init(el, undefined, { renderer: 'canvas' });
}

async function fetchJSON(url) {
  const res = await fetch(url);
  return res.json();
}

const app = createApp({
  delimiters: ['[[', ']]'],
  setup() {
    const keyUsers = ref([]);
    const popup = reactive({ visible: false, data: null });

    async function renderCharts() {
      // Sentiment
      try {
        const sentiment = await fetchJSON('/page/api/sentiment_distribution');
        const chart = initEChart('chart-sentiment');
        if (chart) {
          chart.setOption({
            tooltip: {},
            series: [{ type: 'pie', radius: ['35%', '65%'], data: [
              { name: '正面', value: sentiment.positive || 0 },
              { name: '中性', value: sentiment.neutral || 0 },
              { name: '负面', value: sentiment.negative || 0 },
            ] }]
          });
        }
      } catch {}

      // Gender interests
      try {
        const gender = await fetchJSON('/page/api/gender_interest_data');
        const chart = initEChart('chart-gender');
        if (chart) {
          chart.setOption({
            tooltip: {},
            legend: {},
            xAxis: { type: 'category', data: gender.categories || [] },
            yAxis: { type: 'value' },
            series: (gender.series || []).map(s => ({ ...s, type: 'bar' }))
          });
        }
      } catch {}

      // Map China activity
      try {
        const data = await fetchJSON('/page/api/china_province_activity');
        const chart = initEChart('chart-map');
        if (chart) {
          chart.setOption({
            tooltip: { trigger: 'item' },
            visualMap: { min: 0, max: (data.max || 100), left: 'left', top: 'bottom', text: ['高','低'], calculable: true },
            series: [{
              name: '活跃度',
              type: 'map',
              map: 'china',
              roam: true,
              data: data.items || []
            }]
          });
        }
      } catch {}

      // Word cloud
      try {
        const wc = await fetchJSON('/page/api/word_cloud_data');
        const chart = initEChart('chart-wordcloud');
        if (chart) {
          chart.setOption({
            tooltip: {},
            series: [{
              type: 'wordCloud',
              shape: 'circle',
              gridSize: 8,
              sizeRange: [12, 48],
              rotationRange: [-30, 30],
              textStyle: { color: function () { return '#'+Math.floor(Math.random()*16777215).toString(16); } },
              data: wc || []
            }]
          });
        }
      } catch {}
    }

    async function loadPopup() {
      try {
        const res = await fetch('/announcement/api/popup');
        const data = await res.json();
        if (Array.isArray(data) && data.length > 0) {
          popup.data = data[0];
          popup.visible = true;
        }
      } catch {}
    }

    async function handlePopupRead() {
      try {
        if (popup.data && popup.data.id) {
          await fetch('/announcement/api/mark-as-read', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ id: popup.data.id })
          });
          popup.visible = false;
          updateUnreadCount();
        }
      } catch {}
    }

    onMounted(() => {
      renderCharts();
      updateUnreadCount();
      loadPopup();
      const btn = document.getElementById('update-data-btn');
      if (btn) {
        btn.addEventListener('click', async () => {
          btn.disabled = true; btn.innerText = '更新中...';
          try {
            const res = await fetch('/page/api/update_cache', { method: 'POST' });
            const data = await res.json();
            if (!res.ok) throw new Error(data.message || '更新失败');
            await renderCharts();
            alert('缓存更新成功');
          } catch(e) { alert(e.message); }
          finally { btn.disabled = false; btn.innerText = '更新数据'; }
        });
      }
    });

    // Table data for key users from server-side context if available
    keyUsers.value = (window.key_propagators || []);

    return { keyUsers, popup, handlePopupRead };
  }
});

app.use(ElementPlus);
app.mount('.container-fluid');
