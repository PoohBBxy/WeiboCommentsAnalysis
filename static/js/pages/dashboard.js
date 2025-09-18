import { initCountUpAnimations } from '../utils/animations.js';
import { renderMap } from '../charts/mapChart.js';
import { renderSentimentChart } from '../charts/sentimentChart.js';
import { loadGenderInterestChart } from '../charts/genderInterestChart.js';
import { renderWordCloudChart } from '../charts/wordCloudChart.js';
import { showPopupAnnouncements, updateUnreadCount } from './announcement.js';


/**
 * 对齐卡片高度，使布局更美观
 */
function alignCardHeights() {
    const customerCard = document.getElementById('new-customer-card');
    const commentsCard = document.getElementById('top-comments-card');

    if (customerCard && commentsCard) {
        commentsCard.style.height = 'auto'; // Reset height
        const targetHeight = customerCard.offsetHeight;
        commentsCard.style.height = `${targetHeight}px`;
    }
}

/**
 * 为无效链接绑定 "敬请期待" 提示
 */
function initComingSoonLinks() {
    document.querySelectorAll('a.coming-soon').forEach(link => {
  if (!link.hasAttribute('data-toggle')) {
    link.addEventListener('click', e => {
      e.preventDefault();
      Swal.fire({
        title: "敬请期待",
        text: "此功能正在开发中，感谢您的关注！",
        icon: "info",
        confirmButtonText: "好的"
      });
    });
  }
});
}

/**
 * 绑定 "更新数据" 按钮的事件
 */
function initUpdateDataButton() {
    const updateBtn = document.getElementById('update-data-btn');
    if (updateBtn) {
        updateBtn.addEventListener('click', function() {
            Swal.fire({
                title: "确认更新数据吗？",
                text: "此过程可能需要一些时间，后台将重新计算所有统计数据。",
                icon: "warning",
                showCancelButton: true,
                confirmButtonColor: '#3085d6',
                cancelButtonColor: '#d33',
                confirmButtonText: '立即更新',
                cancelButtonText: '取消'
            }).then((result) => {
                if (result.isConfirmed) {
                    const originalBtnHTML = this.innerHTML;
                    this.innerHTML = `<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> 更新中...`;
                    this.disabled = true;

                    fetch('/page/api/update_cache', { method: 'POST' })
                    .then(response => {
                        // 无论响应成功与否，都先解析JSON
                        return response.json().then(data => {
                            if (!response.ok) {
                                // 如果HTTP状态码表示错误，就抛出一个包含后端消息的Error
                                throw new Error(data.message || '发生未知错误');
                            }
                            return data; // 如果成功，则返回成功的数据
                        });
                    })
                    .then(data => {
                        Swal.fire({
                            title: "更新成功!",
                            text: "数据已是最新，页面即将刷新。",
                            icon: "success",
                            timer: 2500,
                            showConfirmButton: false
                        }).then(() => location.reload());
                    })
                    .catch(error => {
                        console.error('更新失败:', error);
                        Swal.fire({
                            title: "更新失败",
                            text: `${error.message}`,
                            icon: "error",
                            confirmButtonText: "关闭"
                        });
                        this.innerHTML = originalBtnHTML;
                        this.disabled = false;
                    });
                }
            });
        });
    }
}

/**
 * 监听主题(暗/亮模式)切换，并重新渲染所有图表
 * 这是为了确保图表中的颜色（如文字、轴线）能正确更新
 */
function handleThemeChange() {
    const observer = new MutationObserver((mutationsList) => {
        for (const mutation of mutationsList) {
            if (mutation.type === 'attributes' && mutation.attributeName === 'class') {
                // 等待一小段时间，确保CSS样式已应用
                setTimeout(() => {
                    // 重新渲染所有图表以应用新的颜色
                    renderMap();
                    renderSentimentChart();
                    loadGenderInterestChart();
                    renderWordCloudChart();
                }, 150);
            }
        }
    });

    // 观察body元素的class属性变化
    observer.observe(document.body, { attributes: true });
}


/**
 * 页面加载完成后的主入口函数
 */
document.addEventListener('DOMContentLoaded', function() {
    // 初始化所有数字滚动动画
    setTimeout(initCountUpAnimations, 100);

    // 渲染所有图表
    renderMap();
    renderSentimentChart();
    loadGenderInterestChart();
    renderWordCloudChart();

    // 对齐卡片高度
    alignCardHeights();

    initComingSoonLinks();
    initUpdateDataButton();
    handleThemeChange();
    if (!window.__EP_ANNOUNCEMENT__) {
        showPopupAnnouncements();
    }
    updateUnreadCount();



    // 监听窗口大小变化，重新对齐卡片
    window.addEventListener('resize', alignCardHeights);
});
