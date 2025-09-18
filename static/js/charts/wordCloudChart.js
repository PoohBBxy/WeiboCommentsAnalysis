export async function renderWordCloudChart() {
    try {
        const response = await fetch('/page/api/word_cloud_data');
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        const wordCloudData = await response.json();
        const chartDom = document.getElementById('word-cloud-chart');
        if (!chartDom) return;

        if (!wordCloudData || wordCloudData.length === 0) {
            chartDom.innerHTML = '<div style="text-align: center; color: #888;">暂无词云数据</div>';
            return;
        }

        const myChart = echarts.init(chartDom);
        const option = {
            tooltip: { show: true, formatter: params => `${params.name}<br/><b>热度: ${params.value}</b>` },
            series: [{
                textStyle: { fontFamily: 'FZYueJJW' },
                type: 'wordCloud', shape: 'circle', keepAspect: false,
                left: 'center', top: 'center', width: '98%', height: '98%',
                sizeRange: [12, 35], rotationRange: [0, 0], rotationStep: 0,
                gridSize: 5, drawOutOfBound: false, layoutAnimation: true,
                data: wordCloudData
            }]
        };
        myChart.setOption(option);
        window.addEventListener('resize', () => myChart.resize());
    } catch(error) {
        console.error('加载词云图表失败:', error);
        const chartDom = document.getElementById('word-cloud-chart');
        if (chartDom) chartDom.innerHTML = '<div style="color: red; text-align: center;">词云图表加载失败</div>';
    }
}