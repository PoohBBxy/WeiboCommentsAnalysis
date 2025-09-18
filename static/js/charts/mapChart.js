// 中国省份名称映射
const provinceNameMap = {
    '北京': '北京', '天津': '天津', '河北': '河北', '山西': '山西', '内蒙古': '内蒙古',
    '辽宁': '辽宁', '吉林': '吉林', '黑龙江': '黑龙江', '上海': '上海', '江苏': '江苏',
    '浙江': '浙江', '安徽': '安徽', '福建': '福建', '江西': '江西', '山东': '山东',
    '河南': '河南', '湖北': '湖北', '湖南': '湖南', '广东': '广东', '广西': '广西',
    '海南': '海南', '重庆': '重庆', '四川': '四川', '贵州': '贵州', '云南': '云南',
    '西藏': '西藏', '陕西': '陕西', '甘肃': '甘肃', '青海': '青海', '宁夏': '宁夏',
    '新疆': '新疆', '中国台湾': '台湾', '中国香港': '香港', '中国澳门': '澳门', '南海诸岛': '南海诸岛'
};

async function fetchProvinceData() {
    try {
        const response = await fetch('/page/api/china_province_activity');
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        const data = await response.json();
        return Object.keys(data).map(provinceName => ({
            name: provinceNameMap[provinceName] || provinceName,
            value: data[provinceName].heatIndex || 0
        }));
    } catch (error) {
        console.error('获取省份数据失败:', error);
        return [];
    }
}

export async function renderMap() {
    const chartDom = document.getElementById('chart-map-column-04');
    if (!chartDom) return;
    const mapChart = echarts.init(chartDom);
    const provinceData = await fetchProvinceData();
    provinceData.sort((a, b) => b.value - a.value);

    const option = {
        title: {
            text: '', subtext: '活跃度计算规则：1篇文章 + 10热度,\n1评论 + 5热度, 1活跃用户 + 2热度',
            left: 'center', textStyle: {fontSize: 20, fontWeight: 'bold', color: '#333'}
        },
        roam: true,
        tooltip: {
            trigger: 'item',
            formatter: params => (params.data && params.data.value !== undefined) ? `<strong>${params.data.name}</strong><br/>活跃度: ${params.data.value}` : `${params.name}<br/>暂无数据`,
            backgroundColor: 'rgba(255, 255, 255, 0.95)', borderColor: '#eaeaea',
            borderWidth: 1, textStyle: { color: '#333', fontSize: 14 }
        },
        visualMap: {
            left: 'left', top: 'bottom', type: 'piecewise',
            pieces: [
                {gt: 60000, label: '极高活跃度', color: '#d94e5d'},
                {gt: 30000, lte: 60000, label: '高活跃度', color: '#ff704d'},
                {gt: 1000, lte: 30000, label: '中等活跃度 ', color: '#ffb548'},
                {gt: 0, lte: 10000, label: '一般活跃度', color: '#6ee094'},
                {value: 0, label: '无数据/极低活跃度', color: '#ffffff'}
            ],
            orient: 'vertical', inRange: { color: ['#ffffff', '#6ee094', '#ffb548', '#ff704d', '#d94e5d'] },
            textStyle: { color: '#333' }
        },
        toolbox: { show: true, orient: 'vertical', left: 'right', top: 'center', feature: { dataView: {readOnly: true}, restore: {title: '重置'}, saveAsImage: {title: '保存为图片'} } },
        series: [{
            name: '省份活跃度', type: 'map', map: 'china',
            emphasis: { label: { show: true, color: '#fff' }, itemStyle: { areaColor: '#667eea', borderColor: '#fff', borderWidth: 2 } },
            data: provinceData, itemStyle: { borderColor: '#fff', borderWidth: 1 },
            label: { show: false, fontSize: 10, color: '#333' }
        }]
    };
    mapChart.setOption(option);
    window.addEventListener('resize', () => mapChart.resize());
}