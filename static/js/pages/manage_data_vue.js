const { createApp, ref, reactive, onMounted, watch, computed } = Vue;
const { ElMessage, ElMessageBox } = ElementPlus;

const app = createApp({
    delimiters: ['[[', ']]'],
    setup() {
        // --- Reactive State ---
        const activeTab = ref('articles');
        const stats = ref({ articles: 0, comments: 0 });
        const articles = ref([]);
        const comments = ref([]);
        const sentimentLimit = ref(0);

        const loading = reactive({
            stats: true,
            articles: true,
            comments: true,
        });

        const initialArticleFilters = { q: '', isVip: '', start_date: '', end_date: '' };
        const articleFilters = reactive({ ...initialArticleFilters });
        const articleDateRange = ref([]);

        const initialCommentFilters = { q: '', authorGender: '', sentiment: '', start_date: '', end_date: '' };
        const commentFilters = reactive({ ...initialCommentFilters });
        const commentDateRange = ref([]);

        const pagination = reactive({
            articles: { page: 1, limit: 10, total: 0 },
            comments: { page: 1, limit: 10, total: 0 },
        });

        const sentimentSummary = reactive({
            loading: false,
            counts: { total: 0, positive: 0, neutral: 0, negative: 0, none: 0 },
            samples: [],
        });

        const unlabeled = reactive({
            loading: false,
            data: [],
            pagination: { page: 1, limit: 10, total: 0 }
        });

        const sorting = reactive({
            articles: { sortBy: 'created_at', sortOrder: 'desc' },
            comments: { sortBy: 'created_at', sortOrder: 'desc' },
        });

        const dialogs = reactive({
            articleDetail: {
                visible: false,
                data: null,
                comments: {
                    data: [],
                    loading: true,
                    pagination: { page: 1, limit: 10, total: 0 },
                    sorting: { sortBy: 'created_at', sortOrder: 'desc' },
                    filters: { q: '', sentiment: '' }
                }
            },
            commentDetail: {
                visible: false,
                loading: true,
                data: {
                    comment: null,
                    article: null,
                }
            },
            fullComment: { // New dialog for showing full comment
                visible: false,
                content: ''
            },
            edit: { visible: false, type: '', data: null, form: {} },
            missing: {
                visible: false,
                loading: false,
                data: [],
                selected: [],
                options: {
                    max_per_article: 100,
                    max_workers: 8,
                    rpm: 120,
                    delay_min: 3,
                    delay_max: 6,
                    headers: {
                        'Cookie': '',
                        'Referer': 'https://weibo.com/',
                        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
                        'X-Requested-With': 'XMLHttpRequest',
                        'X-XSRF-TOKEN': ''
                    }
                },
                pagination: { page: 1, limit: 10, total: 0 },
                checkId: '',
                checkMsg: '',
            }
        });

        // --- API Helper ---
        const api = async (url, options = {}) => {
            try {
                const response = await fetch(url, options);
                if (response.status === 401) {
                    ElMessage.error('会话已过期，请重新登录');
                    window.location.href = '/user/login';
                    return null;
                }
                if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
                return await response.json();
            } catch (error) {
                console.error("API Error:", error);
                ElMessage.error('请求失败，请检查网络或联系管理员');
                return null;
            }
        };

        // --- Data Fetching Methods ---
        const fetchStats = async () => {
            loading.stats = true;
            const res = await api('/data/api/stats');
            if (res && res.success) stats.value = res.data;
            loading.stats = false;
        };

        const fetchArticles = async (page = 1) => {
            loading.articles = true;
            pagination.articles.page = page;
            const params = new URLSearchParams({
                page,
                limit: pagination.articles.limit,
                sortBy: sorting.articles.sortBy,
                sortOrder: sorting.articles.sortOrder,
                ...articleFilters
            });
            const res = await api(`/data/api/articles?${params}`);
            if (res && res.success) {
                articles.value = res.articles;
                pagination.articles.total = res.pagination.total_records;
            }
            loading.articles = false;
        };

        const exportArticles = () => {
            const params = new URLSearchParams({
                sortBy: sorting.articles.sortBy,
                sortOrder: sorting.articles.sortOrder,
                ...articleFilters
            });
            const url = `/data/api/articles/export?${params.toString()}`;
            window.open(url, '_blank');
        };

        const fetchComments = async (page = 1) => {
            loading.comments = true;
            pagination.comments.page = page;
            const params = new URLSearchParams({
                page,
                limit: pagination.comments.limit,
                sortBy: sorting.comments.sortBy,
                sortOrder: sorting.comments.sortOrder,
                ...commentFilters
            });
            const res = await api(`/data/api/comments?${params}`);
            if (res && res.success) {
                comments.value = res.comments;
                pagination.comments.total = res.pagination.total_records;
            }
            loading.comments = false;
        };

        const exportComments = () => {
            const params = new URLSearchParams({
                sortBy: sorting.comments.sortBy,
                sortOrder: sorting.comments.sortOrder,
                ...commentFilters
            });
            const url = `/data/api/comments/export?${params.toString()}`;
            window.open(url, '_blank');
        };

        const fetchCommentsForArticle = async (page = 1) => {
            const detailState = dialogs.articleDetail;
            detailState.comments.loading = true;
            detailState.comments.pagination.page = page;
            const params = new URLSearchParams({
                articleId: detailState.data.id,
                page,
                limit: detailState.comments.pagination.limit,
                sortBy: detailState.comments.sorting.sortBy,
                sortOrder: detailState.comments.sorting.sortOrder,
                ...detailState.comments.filters
            });
            const res = await api(`/data/api/comments?${params}`);
            if(res && res.success) {
                detailState.comments.data = res.comments;
                detailState.comments.pagination.total = res.pagination.total_records;
            }
            detailState.comments.loading = false;
        };

        // --- Event Handlers ---
        watch(articleDateRange, (newVal) => {
            articleFilters.start_date = newVal ? newVal[0] : '';
            articleFilters.end_date = newVal ? newVal[1] : '';
        });
        watch(commentDateRange, (newVal) => {
            commentFilters.start_date = newVal ? newVal[0] : '';
            commentFilters.end_date = newVal ? newVal[1] : '';
        });

        const resetArticleFilters = () => {
            Object.assign(articleFilters, initialArticleFilters);
            articleDateRange.value = [];
            fetchArticles(1);
        };
        const resetCommentFilters = () => {
            Object.assign(commentFilters, initialCommentFilters);
            commentDateRange.value = [];
            fetchComments(1);
        };

        const handleTabClick = (tab) => {
            if (tab.paneName === 'articles' && articles.value.length === 0) fetchArticles();
            if (tab.paneName === 'comments' && comments.value.length === 0) fetchComments();
            if (tab.paneName === 'sentiment') {
                refreshSentimentSummary();
                fetchUnlabeled();
            }
        };

        const handleSortChange = (type, { prop, order }) => {
            const sortState = sorting[type];
            sortState.sortBy = prop;
            sortState.sortOrder = order === 'ascending' ? 'asc' : 'desc';
            if (type === 'articles') fetchArticles();
            else fetchComments();
        };

        const handleDetailCommentSort = ({ prop, order }) => {
            const sortState = dialogs.articleDetail.comments.sorting;
            sortState.sortBy = prop;
            sortState.sortOrder = order === 'ascending' ? 'asc' : 'desc';
            fetchCommentsForArticle(1);
        };

        // --- Dialog Methods ---
        const showArticleDetails = (row) => {
            dialogs.articleDetail.data = row;
            dialogs.articleDetail.comments.data = [];
            dialogs.articleDetail.comments.pagination.page = 1;
            dialogs.articleDetail.comments.pagination.total = 0;
            dialogs.articleDetail.comments.filters.q = '';
            dialogs.articleDetail.comments.filters.sentiment = '';
            dialogs.articleDetail.visible = true;
            fetchCommentsForArticle();
        };

        const showCommentDetails = async (comment) => {
            const detailState = dialogs.commentDetail;
            detailState.visible = true;
            detailState.loading = true;
            detailState.data = { comment: null, article: null };

            const [commentRes, articleRes] = await Promise.all([
                api(`/data/api/comment/${comment.commentId}`),
                api(`/data/api/article/${comment.articleId}`)
            ]);

            if (commentRes && commentRes.success) {
                detailState.data.comment = commentRes.data;
            } else {
                 ElMessage.error('获取评论详情失败');
            }
            if (articleRes && articleRes.success) {
                detailState.data.article = articleRes.data;
            } else {
                 ElMessage.error('获取关联文章失败');
            }
            detailState.loading = false;
        };

        const showFullComment = (content) => {
            dialogs.fullComment.content = content;
            dialogs.fullComment.visible = true;
        };

        const openEditDialog = (type, data) => {
            dialogs.edit.type = type;
            dialogs.edit.data = data;
            dialogs.edit.form = { ...data };
            dialogs.edit.visible = true;
        };

        // --- CRUD Methods ---
        const submitUpdate = async () => {
            const { type, form } = dialogs.edit;
            const url = type === 'article' ? '/data/api/article/update' : '/data/api/comment/update';
            const res = await api(url, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(form)
            });
            if (res && res.success) {
                ElMessage.success(res.message);
                dialogs.edit.visible = false;
                if (type === 'article') fetchArticles(pagination.articles.page);
                else fetchComments(pagination.comments.page);
            } else {
                ElMessage.error(res ? res.message : '更新失败');
            }
        };

        const handleDelete = (type, id) => {
            ElMessageBox.confirm(
                `确定要删除这条${type === 'article' ? '文章' : '评论'}吗？此操作不可逆。`, '删除确认',
                { confirmButtonText: '确定删除', cancelButtonText: '取消', type: 'warning' }
            ).then(async () => {
                const url = type === 'article' ? '/data/api/article/delete' : '/data/api/comment/delete';
                const res = await api(url, {
                    method: 'POST', headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ id })
                });
                if (res && res.success) {
                    ElMessage.success(res.message);
                    if (type === 'article') fetchArticles(pagination.articles.page);
                    else fetchComments(pagination.comments.page);
                } else {
                     ElMessage.error(res ? res.message : '删除失败');
                }
            }).catch(() => {});
        };

        // --- Formatting & UI Helpers ---
        const formatGender = (gender) => {
            if (gender === '男') return '男';
            if (gender === '女') return '女';
            const g = String(gender || '').toLowerCase();
            if (g === 'm' || g === 'male') return '男';
            if (g === 'f' || g === 'female') return '女';
            return '未知';
        };

        const getSentimentTag = (sentiment) => {
            if (!sentiment) return 'warning';
            if (sentiment === 'positive') return 'success';
            if (sentiment === 'negative') return 'danger';
            if (sentiment === 'neutral') return 'info';
            return 'info';
        };
        const formatSentiment = (sentiment) => {
            const map = { positive: '积极', negative: '消极', neutral: '中性' };
            return sentiment ? (map[sentiment] || sentiment) : '无';
        };

        // --- Missing comments scan & recrawl ---
        const requiredMissingHeaders = ['Cookie', 'Referer', 'User-Agent', 'X-Requested-With', 'X-XSRF-TOKEN'];

        const loadMissingHeaders = async () => {
            const res = await api('/data/api/missing-comments/headers');
            if (res && res.success && res.headers) {
                requiredMissingHeaders.forEach(key => {
                    const value = res.headers[key];
                    dialogs.missing.options.headers[key] = typeof value === 'string' ? value.trim() : (value || '');
                });
            }
        };

        const sanitizeMissingHeaders = () => {
            const result = {};
            requiredMissingHeaders.forEach(key => {
                result[key] = (dialogs.missing.options.headers[key] || '').toString().trim();
            });
            return result;
        };

        const openMissingDialog = async () => {
            dialogs.missing.visible = true;
            dialogs.missing.selected = [];
            dialogs.missing.data = [];
            dialogs.missing.pagination.page = 1;
            dialogs.missing.pagination.total = 0;
            dialogs.missing.checkId = '';
            dialogs.missing.checkMsg = '';
            requiredMissingHeaders.forEach(key => {
                if (!Object.prototype.hasOwnProperty.call(dialogs.missing.options.headers, key)) {
                    dialogs.missing.options.headers[key] = '';
                }
            });
            if (!dialogs.missing.options.headers['Referer']) dialogs.missing.options.headers['Referer'] = 'https://weibo.com/';
            if (!dialogs.missing.options.headers['User-Agent']) dialogs.missing.options.headers['User-Agent'] = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36';
            if (!dialogs.missing.options.headers['X-Requested-With']) dialogs.missing.options.headers['X-Requested-With'] = 'XMLHttpRequest';
            dialogs.missing.options.headers['Cookie'] = dialogs.missing.options.headers['Cookie'] || '';
            dialogs.missing.options.headers['X-XSRF-TOKEN'] = dialogs.missing.options.headers['X-XSRF-TOKEN'] || '';
            await loadMissingHeaders();
            fetchMissing(1);
        };

        const fetchMissing = async (page = 1) => {
            dialogs.missing.loading = true;
            dialogs.missing.pagination.page = page;
            const params = new URLSearchParams({ page, limit: dialogs.missing.pagination.limit });
            const res = await api(`/data/api/missing-comments?${params.toString()}`);
            if (res && res.success) {
                dialogs.missing.data = res.items || [];
                dialogs.missing.pagination.total = res.pagination?.total || 0;
            }
            dialogs.missing.loading = false;
        };

        const missingSelectionAll = computed(() => {
            const ids = dialogs.missing.data.map(item => item.id);
            if (!ids.length) return false;
            return ids.every(id => dialogs.missing.selected.includes(id));
        });

        const missingSelectionIndeterminate = computed(() => {
            if (!dialogs.missing.data.length) return false;
            const selectedCount = dialogs.missing.data.reduce((acc, item) => acc + (dialogs.missing.selected.includes(item.id) ? 1 : 0), 0);
            return selectedCount > 0 && selectedCount < dialogs.missing.data.length;
        });

        const isMissingSelected = (id) => dialogs.missing.selected.includes(id);

        const toggleMissingRow = (id, checked) => {
            const idx = dialogs.missing.selected.indexOf(id);
            if (checked) {
                if (idx === -1) dialogs.missing.selected.push(id);
            } else if (idx !== -1) {
                dialogs.missing.selected.splice(idx, 1);
            }
        };

        const toggleMissingSelectAll = (checked) => {
            const pageIds = dialogs.missing.data.map(item => item.id);
            if (checked) {
                const unique = new Set(dialogs.missing.selected);
                pageIds.forEach(id => unique.add(id));
                dialogs.missing.selected = Array.from(unique);
            } else {
                dialogs.missing.selected = dialogs.missing.selected.filter(id => !pageIds.includes(id));
            }
        };

        const startRecrawl = async () => {
            if (dialogs.missing.selected.length === 0) {
                ElMessage.warning('请先选择文章');
                return;
            }
            const headersPayload = sanitizeMissingHeaders();
            const missingHeader = requiredMissingHeaders.find(key => !headersPayload[key]);
            if (missingHeader) {
                ElMessage.error(`Headers 缺失（${missingHeader}），请补充后再试`);
                return;
            }
            requiredMissingHeaders.forEach(key => {
                dialogs.missing.options.headers[key] = headersPayload[key];
            });
            const clampInt = (val, min, max) => {
                const num = Number(val);
                if (Number.isNaN(num)) return min;
                if (typeof max === 'number') return Math.max(min, Math.min(max, num));
                return Math.max(min, num);
            };
            const clampFloat = (val, fallback) => {
                const num = Number(val);
                return Number.isNaN(num) ? fallback : num;
            };
            const maxWorkers = clampInt(dialogs.missing.options.max_workers, 1, 20);
            const rpm = clampInt(dialogs.missing.options.rpm, 1, 360);
            const maxPerArticle = clampInt(dialogs.missing.options.max_per_article, 1);
            const delayMin = Math.max(0, clampFloat(dialogs.missing.options.delay_min, 3));
            const delayMax = Math.max(delayMin, clampFloat(dialogs.missing.options.delay_max, delayMin));
            dialogs.missing.options.max_workers = maxWorkers;
            dialogs.missing.options.rpm = rpm;
            dialogs.missing.options.max_per_article = maxPerArticle;
            dialogs.missing.options.delay_min = delayMin;
            dialogs.missing.options.delay_max = delayMax;
            try {
                await ElMessageBox.confirm(`将对 ${dialogs.missing.selected.length} 篇文章发起补爬，确认开始吗？`, '创建补爬任务', { type: 'warning', confirmButtonText: '确认', cancelButtonText: '取消' });
            } catch (_) { return; }
            const optionsPayload = {
                max_per_article: maxPerArticle,
                max_workers: maxWorkers,
                rpm,
                delay_min: delayMin,
                delay_max: delayMax,
                headers: headersPayload,
            };
            const payload = {
                article_ids: dialogs.missing.selected,
                options: optionsPayload,
            };
            const res = await api('/data/api/recrawl/create-task', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
            if (res && res.success) {
                ElMessage.success(res.message || '已创建任务，请前往任务管理启动');
                dialogs.missing.visible = false;
            } else {
                ElMessage.error(res ? res.message : '补爬启动失败');
            }
        };

        const selectAllMissing = () => { toggleMissingSelectAll(true); };

        const deleteSelectedMissing = async () => {
            const ids = dialogs.missing.selected.slice();
            if (!ids.length) { ElMessage.warning('请先选择'); return; }
            try {
                await ElMessageBox.confirm(`确认删除选中的 ${ids.length} 项记录吗？`, '删除所选', { type: 'warning', confirmButtonText: '确认', cancelButtonText: '取消' });
                await ElMessageBox.confirm('该操作不可恢复，是否继续？', '再次确认', { type: 'error', confirmButtonText: '仍要删除', cancelButtonText: '取消' });
            } catch (_) { return; }
            const res = await api('/data/api/missing-comments/batch-delete', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ ids }) });
            if (res && res.success) {
                ElMessage.success('删除成功');
                dialogs.missing.selected = [];
                fetchMissing(dialogs.missing.pagination.page);
            } else {
                ElMessage.error(res ? res.message : '删除失败');
            }
        };

        const clearMissingSelection = () => {
            dialogs.missing.selected = [];
        };

        const selectAllMissingAll = async () => {
            const res = await api('/data/api/missing-comments/all');
            if (res && res.success) {
                const ids = Array.isArray(res.ids) ? res.ids : [];
                dialogs.missing.selected = Array.from(new Set(ids));
                ElMessage.success(`已全选 ${dialogs.missing.selected.length} 篇`);
            } else {
                ElMessage.error(res ? res.message : '获取失败');
            }
        };

        const checkMissingById = async () => {
            const id = (dialogs.missing.checkId || '').trim();
            if (!id) { dialogs.missing.checkMsg = '请输入文章ID'; return; }
            dialogs.missing.checkMsg = '检查中...';
            const params = new URLSearchParams({ articleId: id });
            const res = await api(`/data/api/missing-comments/check?${params.toString()}`);
            if (!res) { dialogs.missing.checkMsg = '检查失败'; return; }
            if (!res.success) { dialogs.missing.checkMsg = res.message || '检查失败'; return; }
            if (res.qualifies && res.item) {
                // prepend or update the list with the single item and select it
                const exists = dialogs.missing.data.find(x => x.id === res.item.id);
                if (!exists) dialogs.missing.data.unshift(res.item);
                if (!dialogs.missing.selected.includes(res.item.id)) {
                    dialogs.missing.selected.push(res.item.id);
                }
                dialogs.missing.checkMsg = '该文章符合条件，已添加并选中';
            } else {
                dialogs.missing.checkMsg = '该文章不符合条件（可能评论数为0或已存在评论）';
            }
        };

        // --- Sentiment analysis ---
        const runSentimentAnalysis = async () => {
            try {
                await ElMessageBox.confirm('将对 sentiment_label 为空的评论执行情感分析，可能较慢。是否继续？', '情感分析', { type: 'warning' });
            } catch (_) { return; }
            const payload = { limit: Number(sentimentLimit.value || 0) };
            const res = await api('/data/api/sentiment/analyze-new', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
            if (res && res.success) {
                ElMessage.success(`分析完成，处理 ${res.analyzed || 0} 条，更新 ${res.updated || 0} 条`);
                if (activeTab.value === 'comments') fetchComments(pagination.comments.page);
                refreshSentimentSummary();
                fetchUnlabeled(unlabeled.pagination.page);
            } else {
                ElMessage.error(res ? res.message : '分析失败');
            }
        };

        const refreshSentimentSummary = async () => {
            sentimentSummary.loading = true;
            const res = await api('/data/api/sentiment/summary');
            if (res && res.success) {
                sentimentSummary.counts = res.counts || sentimentSummary.counts;
                sentimentSummary.samples = res.samples || [];
            }
            sentimentSummary.loading = false;
        };

        const fetchUnlabeled = async (page = 1) => {
            unlabeled.loading = true;
            unlabeled.pagination.page = page;
            const params = new URLSearchParams({
                page,
                limit: unlabeled.pagination.limit,
                sortBy: 'created_at',
                sortOrder: 'desc',
                sentiment: 'none'
            });
            const res = await api(`/data/api/comments?${params}`);
            if (res && res.success) {
                unlabeled.data = res.comments;
                unlabeled.pagination.total = res.pagination.total_records;
            }
            unlabeled.loading = false;
        };

        const handleUnlabeledSizeChange = (size) => {
            unlabeled.pagination.limit = size;
            fetchUnlabeled(1);
        };

        // --- Initial Load ---
        onMounted(() => {
            fetchStats();
            fetchArticles();
            refreshSentimentSummary();
            fetchUnlabeled();
        });

        return {
            activeTab, stats, articles, comments, loading,
            articleFilters, articleDateRange, commentFilters, commentDateRange,
            pagination, dialogs,
            sentimentSummary,
            unlabeled,
            fetchArticles, fetchComments, fetchCommentsForArticle,
            resetArticleFilters, resetCommentFilters,
            handleTabClick, handleSortChange, handleDetailCommentSort,
            showArticleDetails, showCommentDetails, openEditDialog, showFullComment,
            submitUpdate, handleDelete,
            formatGender, getSentimentTag, formatSentiment,
            exportArticles, exportComments,
            // missing comments recrawl
            openMissingDialog, fetchMissing, startRecrawl, checkMissingById, selectAllMissing, clearMissingSelection, selectAllMissingAll, deleteSelectedMissing,
            missingSelectionAll, missingSelectionIndeterminate, isMissingSelected, toggleMissingRow, toggleMissingSelectAll,
            // sentiment
            runSentimentAnalysis, sentimentLimit, refreshSentimentSummary, fetchUnlabeled, handleUnlabeledSizeChange,
        };
    }
});

// Register all Element Plus icons
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
    app.component(key, component);
}
app.use(ElementPlus);
app.mount('#data-management-app');
