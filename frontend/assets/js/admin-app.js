        const apiBasePath = '/api/v1';
        const tokenStorageKey = 'admin.accessToken';
        const userStorageKey = 'admin.user';
        const ORDER_CONTACT_METHODS = ['WA', 'TG', 'AV', 'IG', 'SMS', 'MX'];

        const state = {
            accessToken: localStorage.getItem(tokenStorageKey) || '',
            user: JSON.parse(localStorage.getItem(userStorageKey) || 'null'),
            setupStatus: null,
            users: [],
            messages: [],
            orders: [],
            inventories: [],
            productRegistrations: [],
            auditEvents: [],
            auditSelectedDate: getTodayDateValue(),
            auditLoading: false,
            auditError: '',
            establishments: [],
            orderMethods: [],
            statuses: [],
            currencies: [],
            pendingUsers: [],
            productsTotal: 0,
            auditEvents: [],
            auditSelectedDate: getTodayDateValue(),
            auditLoading: false,
            auditError: '',
            lastProductImport: null,
            isProductImportRunning: false,
            currentProductImportJobId: '',
            productImportStatus: '',
            productImportStatusType: '',
            orderImport: {
                rawText: '',
                parsedRows: [],
                loading: false,
                status: '',
                statusType: '',
            },
            orderDraft: {
                order_establishment_id: '',
                order_method_id: '',
                order_sub_method: '',
                order_contact_method: '',
                order_customer: '',
                message_text: '',
                order_info: '',
                order_status_id: '',
                items: [createOrderItemDraft()],
            },
            inventoryProductSearch: createSingleProductSearchState(),
            productRegistrationProductSearch: createSingleProductSearchState(),
            orderManagement: {
                items: [],
                pagination: { page: 1, page_size: 50, total: 0, total_pages: 0 },
                filters: {
                    search: '',
                    establishment_id: '',
                    method_id: '',
                    status_id: '',
                },
                loading: false,
                loadingOrderID: null,
                savingOrderID: null,
                expandedOrderID: null,
                editors: {},
                statusDrafts: {},
            },
            contactsView: {
                items: [],
                pagination: { page: 1, page_size: 50, total: 0, total_pages: 0 },
                type: 'buyer',
                search: '',
                loading: false,
            },
            editing: {},
            activeMenu: 'order-create',
        };

        const loginView = document.getElementById('login-view');
        const dashboardView = document.getElementById('dashboard-view');
        const loginForm = document.getElementById('login-form');
        const bootstrapForm = document.getElementById('bootstrap-form');
        const loginMessage = document.getElementById('login-message');
        const dashboardMessage = document.getElementById('dashboard-message');
        const dashboardMeta = document.getElementById('dashboard-meta');
        const dashboardMenu = document.getElementById('dashboard-menu');
        const authTitle = document.getElementById('auth-title');
        const authDescription = document.getElementById('auth-description');
        const setupNote = document.getElementById('setup-note');

        const cards = {
            messageSender: document.getElementById('card-message-sender'),
            orderCreate: document.getElementById('card-order-create'),
            inventoryCreate: document.getElementById('card-inventory-create'),
            productRegistrationCreate: document.getElementById('card-product-registration-create'),
            orderManagement: document.getElementById('card-order-management'),
            contacts: document.getElementById('card-contacts'),
            pendingUsers: document.getElementById('card-pending-users'),
            users: document.getElementById('card-users'),
            audit: document.getElementById('card-audit'),
            productImport: document.getElementById('card-product-import'),
            establishments: document.getElementById('card-establishments'),
            orderMethods: document.getElementById('card-order-methods'),
            statuses: document.getElementById('card-statuses'),
            currencies: document.getElementById('card-currencies'),
        };

        const dashboardMenuItems = [
            { id: 'order-create', title: 'Заказ' },
            { id: 'receipts', title: 'Приемки' },
            { id: 'inventory', title: 'Инвентаризация' },
            { id: 'orders', title: 'Все заказы' },
            { id: 'counterparties', title: 'Контрагенты' },
            { id: 'communication', title: 'Чат' },
            { id: 'users', title: 'Пользователи' },
            { id: 'audit', title: 'Аудит' },
            { id: 'catalogs', title: 'Справочники' },
            { id: 'import', title: 'Импорт' },
        ];

        function getTodayDateValue() {
            const now = new Date();
            const year = now.getFullYear();
            const month = String(now.getMonth() + 1).padStart(2, '0');
            const day = String(now.getDate()).padStart(2, '0');
            return `${year}-${month}-${day}`;
        }

        function setMessage(target, text, type = '') {
            target.textContent = text || '';
            target.className = `message${type ? ` ${type}` : ''}`;
        }

        function isBootstrapRequired() {
            return Boolean(state.setupStatus?.bootstrap_required);
        }

        function showSetupNote(text) {
            if (!text) {
                setupNote.classList.add('hidden');
                setupNote.innerHTML = '';
                return;
            }

            setupNote.classList.remove('hidden');
            setupNote.innerHTML = text;
        }

        function renderAuthMode() {
            const bootstrapRequired = isBootstrapRequired();

            authTitle.textContent = bootstrapRequired ? 'Первый администратор' : 'Вход';
            authDescription.textContent = bootstrapRequired
                ? 'База данных пуста. Создай первого пользователя с правами администратора и активным статусом.'
                : 'Используй логин и пароль администратора backend.';

            loginForm.classList.toggle('hidden', bootstrapRequired);
            bootstrapForm.classList.toggle('hidden', !bootstrapRequired);

            if (bootstrapRequired) {
                showSetupNote('Этот экран вызывает <strong>/api/v1/users/bootstrap</strong> и доступен только пока в системе нет ни одного пользователя. Для создания первого администратора нужен bootstrap-ключ.');
            } else {
                showSetupNote('Если база уже инициализирована, вход выполняется только существующим пользователем с флагом <strong>user_admin</strong>.');
            }
        }

        function escapeHtml(value) {
            return String(value ?? '')
                .replaceAll('&', '&amp;')
                .replaceAll('<', '&lt;')
                .replaceAll('>', '&gt;')
                .replaceAll('"', '&quot;')
                .replaceAll("'", '&#39;');
        }

        async function request(path, options = {}) {
            const isFormData = options.body instanceof FormData;
            const headers = {
                Accept: 'application/json',
                ...(state.accessToken ? { Authorization: `Bearer ${state.accessToken}` } : {}),
                ...(options.headers || {}),
            };

            if (!isFormData && !headers['Content-Type']) {
                headers['Content-Type'] = 'application/json';
            }

            const response = await fetch(`${apiBasePath}${path}`, {
                ...options,
                headers,
            });

            const text = await response.text();
            const contentType = (response.headers.get('content-type') || '').toLowerCase();
            let payload = null;

            if (text) {
                if (contentType.includes('application/json')) {
                    try {
                        payload = JSON.parse(text);
                    } catch {
                        throw new Error(`Backend вернул повреждённый JSON (HTTP ${response.status})`);
                    }
                } else if (text.trim().startsWith('{') || text.trim().startsWith('[')) {
                    try {
                        payload = JSON.parse(text);
                    } catch {
                        payload = null;
                    }
                }
            }

            if (!response.ok) {
                const plainText = text.replace(/\s+/g, ' ').trim();
                if (payload?.error?.message) {
                    throw new Error(payload.error.message);
                }
                if (contentType.includes('text/html')) {
                    if (response.status === 413) {
                        throw new Error('Файл слишком большой для nginx frontend. Нужно увеличить client_max_body_size и перезапустить frontend контейнер.');
                    }
                    if (response.status === 504) {
                        throw new Error('Импорт не успел завершиться в таймаут nginx. Нужно увеличить proxy_read_timeout и перезапустить frontend контейнер.');
                    }
                    throw new Error(`Frontend/nginx вернул HTML вместо JSON (HTTP ${response.status}).`);
                }
                throw new Error(plainText || `HTTP ${response.status}`);
            }

            return payload;
        }

        async function loadSetupStatus() {
            state.setupStatus = await request('/setup-status', { method: 'GET' });
            renderAuthMode();
            return state.setupStatus;
        }

        async function checkBackendHealth() {
            const live = await fetch(`${apiBasePath}/health/live`);
            if (!live.ok) {
                throw new Error('Backend API недоступен');
            }

            const ready = await fetch(`${apiBasePath}/health/ready`);
            if (!ready.ok) {
                throw new Error('Database недоступна');
            }
        }

        async function ensureAdminSession() {
            if (!state.accessToken) {
                try {
                    await loadSetupStatus();
                } catch (error) {
                    setMessage(loginMessage, error.message, 'error');
                }
                showLogin();
                return;
            }

            try {
                const payload = await request('/auth/me', { method: 'GET' });
                if (!payload.user.user_admin) {
                    throw new Error('В web admin может войти только пользователь с user_admin = true');
                }
                state.user = payload.user;
                persistSession();
                await loadDashboardData();
                showDashboard();
            } catch (error) {
                clearSession();
                try {
                    await loadSetupStatus();
                } catch (setupError) {
                    setMessage(loginMessage, setupError.message, 'error');
                }
                showLogin();
                setMessage(loginMessage, error.message, 'error');
            }
        }

        function persistSession() {
            localStorage.setItem(tokenStorageKey, state.accessToken);
            localStorage.setItem(userStorageKey, JSON.stringify(state.user));
        }

        function clearSession() {
            state.accessToken = '';
            state.user = null;
            state.setupStatus = null;
            state.users = [];
            state.messages = [];
            state.orders = [];
            state.inventories = [];
            state.productRegistrations = [];
            state.auditEvents = [];
            state.auditSelectedDate = getTodayDateValue();
            state.auditLoading = false;
            state.auditError = '';
            state.establishments = [];
            state.orderMethods = [];
            state.statuses = [];
            state.currencies = [];
            state.pendingUsers = [];
            state.productsTotal = 0;
            state.lastProductImport = null;
            state.isProductImportRunning = false;
            state.currentProductImportJobId = '';
            state.productImportStatus = '';
            state.productImportStatusType = '';
            state.orderImport = {
                rawText: '',
                parsedRows: [],
                loading: false,
                status: '',
                statusType: '',
            };
            state.orderManagement = {
                items: [],
                pagination: { page: 1, page_size: 50, total: 0, total_pages: 0 },
                filters: {
                    search: '',
                    establishment_id: '',
                    method_id: '',
                    status_id: '',
                },
                loading: false,
                loadingOrderID: null,
                savingOrderID: null,
                expandedOrderID: null,
                editors: {},
                statusDrafts: {},
            };
            state.contactsView = {
                items: [],
                pagination: { page: 1, page_size: 50, total: 0, total_pages: 0 },
                type: 'buyer',
                search: '',
                loading: false,
            };
            resetOrderDraft();
            resetSingleDocumentProductSearch('inventory');
            resetSingleDocumentProductSearch('productRegistration');
            state.editing = {};
            state.activeMenu = 'order-create';
            localStorage.removeItem(tokenStorageKey);
            localStorage.removeItem(userStorageKey);
        }

        function showLogin() {
            loginView.classList.remove('hidden');
            dashboardView.classList.add('hidden');
        }

        function showDashboard() {
            loginView.classList.add('hidden');
            dashboardView.classList.remove('hidden');
            renderDashboardMeta();
            renderAllCards();
        }

        function renderDashboardMenu() {
            dashboardMenu.innerHTML = dashboardMenuItems.map((item) => `
                <button class="menu-button${state.activeMenu === item.id ? ' active' : ''}" type="button" data-dashboard-menu="${item.id}">${escapeHtml(item.title)}</button>
            `).join('');
        }

        function applyDashboardMenuVisibility() {
            document.querySelectorAll('[data-menu]').forEach((element) => {
                element.classList.toggle('hidden', element.dataset.menu !== state.activeMenu);
            });
        }

        function renderDashboardMeta() {
            if (!state.user) {
                dashboardMeta.innerHTML = '';
                return;
            }

            dashboardMeta.innerHTML = [
                `<span class="pill">${escapeHtml(state.user.user_login)}</span>`,
                `<span class="pill">${escapeHtml(state.user.user_second_name || '')} ${escapeHtml(state.user.user_first_name || '')}</span>`,
                `<span class="pill">admin only</span>`
            ].join('');
        }

        async function loginAsAdmin(login, password) {
            const payload = await request('/auth/login', {
                method: 'POST',
                body: JSON.stringify({ user_login: login, user_password: password }),
            });

            if (!payload.user.user_admin) {
                throw new Error('В web admin может войти только пользователь с user_admin = true');
            }

            state.accessToken = payload.access_token || payload.token;
            state.user = payload.user;
            persistSession();
            await loadDashboardData();
            showDashboard();
        }

        async function bootstrapAdmin(formData) {
            const payload = await request('/users/bootstrap', {
                method: 'POST',
                body: JSON.stringify({
                    first_admin_pass: formData.get('first_admin_pass'),
                    user_login: formData.get('user_login'),
                    user_password: formData.get('user_password'),
                    user_first_name: formData.get('user_first_name'),
                    user_second_name: formData.get('user_second_name'),
                    user_age: Number(formData.get('user_age')),
                    user_address: formData.get('user_address'),
                    user_admin: true,
                    user_active: true,
                }),
            });

            if (!payload.user?.user_admin) {
                throw new Error('Backend вернул пользователя без прав администратора');
            }

            state.accessToken = payload.access_token || payload.token;
            state.user = payload.user;
            state.setupStatus = { users_count: 1, bootstrap_required: false };
            persistSession();
            await loadDashboardData();
            showDashboard();
        }

        async function loadDashboardData() {
            const [users, messages, orders, inventories, productRegistrations, establishments, orderMethods, statuses, currencies, products] = await Promise.all([
                request('/users?page=1&page_size=100&sort_by=user_created_at&sort_order=desc', { method: 'GET' }),
                request('/messages?page=1&page_size=100', { method: 'GET' }),
                request('/orders?page=1&page_size=20', { method: 'GET' }),
                request('/inventories?page=1&page_size=20', { method: 'GET' }),
                request('/product-registrations?page=1&page_size=20', { method: 'GET' }),
                request('/establishments', { method: 'GET' }),
                request('/order-methods', { method: 'GET' }),
                request('/statuses', { method: 'GET' }),
                request('/currencies', { method: 'GET' }),
                request('/products?page=1&page_size=1', { method: 'GET' }),
            ]);

            state.users = users.items || [];
            state.messages = sortMessagesAscending(messages.items || []);
            state.orders = orders.items || [];
            state.inventories = inventories.items || [];
            state.productRegistrations = productRegistrations.items || [];
            state.pendingUsers = state.users.filter((item) => !item.user_active);
            state.establishments = establishments.items || [];
            state.orderMethods = orderMethods.items || [];
            state.statuses = statuses.items || [];
            state.currencies = currencies.items || [];
            state.productsTotal = products.pagination?.total || 0;
            ensureOrderDraftDefaults();
            await loadAuditEvents({ silent: true });
            if (state.activeMenu === 'orders') {
                await loadOrderManagementPage({ page: state.orderManagement.pagination.page || 1, silent: true });
            }
            if (state.activeMenu === 'counterparties') {
                await loadContactsPage({ page: state.contactsView.pagination.page || 1, silent: true });
            }
            renderAllCards();
        }

        async function loadMessages() {
            const messages = await request('/messages?page=1&page_size=100', { method: 'GET' });
            state.messages = sortMessagesAscending(messages.items || []);
            renderMessageSender();
        }

        function sortMessagesAscending(items) {
            return [...items].sort((left, right) => {
                const leftTime = Date.parse(left.message_created_at || '') || 0;
                const rightTime = Date.parse(right.message_created_at || '') || 0;
                if (leftTime !== rightTime) {
                    return leftTime - rightTime;
                }
                return (left.message_id || 0) - (right.message_id || 0);
            });
        }

        function getAuditDateRange(selectedDate) {
            const dateValue = selectedDate || getTodayDateValue();
            return {
                dateFrom: `${dateValue}T00:00:00`,
                dateTo: `${dateValue}T23:59:59`,
            };
        }

        async function loadAuditEvents({ silent = false } = {}) {
            if (!state.auditSelectedDate) {
                state.auditSelectedDate = getTodayDateValue();
            }

            if (!silent) {
                state.auditLoading = true;
                renderAuditEvents();
            }

            const { dateFrom, dateTo } = getAuditDateRange(state.auditSelectedDate);
            const params = new URLSearchParams({
                date_from: dateFrom,
                date_to: dateTo,
                page: '1',
                page_size: '100',
            });

            try {
                const payload = await request(`/audit-events?${params.toString()}`, { method: 'GET' });
                state.auditEvents = payload.items || [];
                state.auditError = '';
            } catch (error) {
                state.auditEvents = [];
                state.auditError = error.message;
            } finally {
                state.auditLoading = false;
                renderAuditEvents();
            }
        }

        function formatAuditTimestamp(value) {
            if (!value) {
                return 'время неизвестно';
            }

            const date = new Date(value);
            if (Number.isNaN(date.getTime())) {
                return value;
            }

            return date.toLocaleString('ru-RU', {
                year: 'numeric',
                month: '2-digit',
                day: '2-digit',
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit',
            });
        }

        function formatAuditPayload(payload) {
            if (!payload || (typeof payload === 'object' && !Object.keys(payload).length)) {
                return 'Payload отсутствует';
            }

            try {
                return JSON.stringify(payload, null, 2);
            } catch {
                return String(payload);
            }
        }

        function truncateAuditText(value, maxLength = 140) {
            const text = String(value || '').trim();
            if (!text) {
                return '';
            }
            return text.length > maxLength ? `${text.slice(0, maxLength - 1)}…` : text;
        }

        function quoteAuditText(value) {
            const text = truncateAuditText(value);
            return text ? `«${text}»` : '';
        }

        function formatActorLabel(item) {
            return item.actor_user_login || (item.actor_user_id ? `Пользователь #${item.actor_user_id}` : 'Система');
        }

        function formatEntityLabel(item) {
            if (!item.entity_id) {
                return item.entity_type || 'объект';
            }

            switch (item.entity_type) {
                case 'order':
                    return `заказе #${item.entity_id}`;
                case 'inventory':
                    return `инвентаризации #${item.entity_id}`;
                case 'product_registration':
                    return `приемке #${item.entity_id}`;
                case 'message':
                    return `сообщении #${item.entity_id}`;
                case 'document':
                    return `документе #${item.entity_id}`;
                case 'user':
                    return `пользователе #${item.entity_id}`;
                default:
                    return `${item.entity_type || 'объекте'} #${item.entity_id}`;
            }
        }

        function summarizeStatusChange(change) {
            if (!change || typeof change !== 'object') {
                return '';
            }
            const fromValue = change.from ?? 'не задан';
            const toValue = change.to ?? 'не задан';
            return `с «${fromValue}» на «${toValue}»`;
        }

        function describeAuditEvent(item) {
            const actor = formatActorLabel(item);
            const payload = item.event_payload || {};
            const details = [];
            let title = item.event_type || 'Событие';
            let rawPayload = false;

            switch (item.event_type) {
                case 'message.create': {
                    if (payload.message_type === 'message') {
                        title = `${actor} оставил сообщение`;
                        if (payload.message_text) {
                            details.push(`Текст сообщения: ${quoteAuditText(payload.message_text)}`);
                        }
                    } else {
                        title = `${actor} отправил вложение в общий чат`;
                        if (payload.attachments_count) {
                            details.push(`Количество вложений: ${payload.attachments_count}`);
                        }
                    }
                    break;
                }
                case 'message.update': {
                    title = `${actor} изменил сообщение`;
                    if (payload.previous_message_text || payload.message_text) {
                        details.push(`Было: ${quoteAuditText(payload.previous_message_text) || 'пусто'}`);
                        details.push(`Стало: ${quoteAuditText(payload.message_text) || 'пусто'}`);
                    }
                    break;
                }
                case 'message.delete': {
                    title = `${actor} удалил сообщение`;
                    if (payload.message_text) {
                        details.push(`Удаленный текст: ${quoteAuditText(payload.message_text)}`);
                    }
                    if (payload.attachments_count) {
                        details.push(`Удалено вложений: ${payload.attachments_count}`);
                    }
                    break;
                }
                case 'order.comment.create': {
                    title = `${actor} оставил комментарий в ${formatEntityLabel(item)}`;
                    if (payload.order_comment_text) {
                        details.push(`Комментарий: ${quoteAuditText(payload.order_comment_text)}`);
                    }
                    if (payload.attachment_count) {
                        details.push(`Приложено вложений: ${payload.attachment_count}`);
                    }
                    break;
                }
                case 'order.create': {
                    title = `${actor} создал заказ #${item.entity_id || '?'}`;
                    if (payload.order?.order_customer) {
                        details.push(`Клиент: ${payload.order.order_customer}`);
                    }
                    if (payload.items_count) {
                        details.push(`Количество позиций: ${payload.items_count}`);
                    }
                    break;
                }
                case 'order.update': {
                    title = `${actor} обновил заказ #${item.entity_id || '?'}`;
                    const changedFields = payload.changed_fields || {};
                    if (changedFields.order_status) {
                        title = `${actor} сменил статус заказа #${item.entity_id || '?'}`;
                        details.push(`Статус заказа: ${summarizeStatusChange(changedFields.order_status)}`);
                    }

                    const itemUpdates = Array.isArray(payload.items?.updated) ? payload.items.updated : [];
                    itemUpdates.forEach((entry) => {
                        const statusChange = entry?.changes?.order_item_status;
                        if (!statusChange) {
                            return;
                        }
                        const itemName = entry.after?.order_item_name || entry.before?.order_item_name || 'товар';
                        details.push(`Статус товара ${quoteAuditText(itemName)}: ${summarizeStatusChange(statusChange)}`);
                    });

                    if (!details.length) {
                        rawPayload = true;
                    }
                    break;
                }
                case 'inventory.create': {
                    title = `${actor} создал инвентаризацию #${item.entity_id || '?'}`;
                    if (payload.items_count) {
                        details.push(`Количество позиций: ${payload.items_count}`);
                    }
                    break;
                }
                case 'inventory.update': {
                    title = `${actor} обновил инвентаризацию #${item.entity_id || '?'}`;
                    rawPayload = true;
                    break;
                }
                case 'product_registration.create': {
                    title = `${actor} создал приемку #${item.entity_id || '?'}`;
                    if (payload.items_count) {
                        details.push(`Количество позиций: ${payload.items_count}`);
                    }
                    break;
                }
                case 'product_registration.update': {
                    title = `${actor} обновил приемку #${item.entity_id || '?'}`;
                    rawPayload = true;
                    break;
                }
                case 'document.create': {
                    title = `${actor} создал документ #${item.entity_id || '?'}`;
                    if (payload.document_kind) {
                        details.push(`Тип документа: ${payload.document_kind}`);
                    }
                    if (payload.document_status) {
                        details.push(`Статус документа: ${payload.document_status}`);
                    }
                    break;
                }
                case 'document.update': {
                    title = `${actor} обновил документ #${item.entity_id || '?'}`;
                    if (Array.isArray(payload.changed_fields) && payload.changed_fields.length) {
                        details.push(`Изменены поля: ${payload.changed_fields.join(', ')}`);
                    }
                    if (payload.document_status) {
                        details.push(`Новый статус: ${payload.document_status}`);
                    }
                    break;
                }
                case 'user.create':
                    title = `${actor} создал пользователя`;
                    if (payload.user_login) {
                        details.push(`Логин: ${payload.user_login}`);
                    }
                    break;
                case 'user.update':
                    title = `${actor} изменил пользователя #${item.entity_id || '?'}`;
                    if (Array.isArray(payload.changed_fields) && payload.changed_fields.length) {
                        details.push(`Изменены поля: ${payload.changed_fields.join(', ')}`);
                    }
                    break;
                case 'auth.login.succeeded':
                    title = `${actor} успешно вошел в систему`;
                    break;
                case 'auth.login.failed':
                    title = `Неудачная попытка входа`;
                    if (payload.user_login) {
                        details.push(`Логин: ${payload.user_login}`);
                    }
                    if (payload.reason) {
                        details.push(`Причина: ${payload.reason}`);
                    }
                    break;
                default:
                    title = `${actor} выполнил действие ${item.event_type || 'event'}`;
                    rawPayload = true;
                    break;
            }

            if (!details.length && !rawPayload && payload && Object.keys(payload).length) {
                rawPayload = true;
            }

            return { title, details, rawPayload };
        }

        function getAuditCategory(item) {
            const eventType = String(item?.event_type || '');

            if (eventType === 'auth.login.failed') {
                return { label: 'Ошибка входа', className: 'audit-pill-error' };
            }

            if (eventType.startsWith('auth.')) {
                return { label: 'Авторизация', className: 'audit-pill-auth' };
            }

            if (eventType.endsWith('.create') || eventType.endsWith('.bootstrap') || eventType.endsWith('.register')) {
                return { label: 'Создание', className: 'audit-pill-create' };
            }

            if (eventType.endsWith('.update')) {
                return { label: 'Изменение', className: 'audit-pill-update' };
            }

            if (eventType.endsWith('.delete')) {
                return { label: 'Удаление', className: 'audit-pill-delete' };
            }

            return { label: 'Событие', className: 'audit-pill-neutral' };
        }

        function renderAuditEventRow(item) {
            const actor = item.actor_user_login || (item.actor_user_id ? `user #${item.actor_user_id}` : 'system');
            const entity = item.entity_id ? `${item.entity_type} #${item.entity_id}` : (item.entity_type || 'без entity');
            const description = describeAuditEvent(item);
            const category = getAuditCategory(item);
            const detailsHtml = description.details.length
                ? `<div class="audit-details">${description.details.map((line) => `<div class="audit-detail-line">${escapeHtml(line)}</div>`).join('')}</div>`
                : '';
            const payloadHtml = description.rawPayload
                ? `<pre class="audit-payload">${escapeHtml(formatAuditPayload(item.event_payload))}</pre>`
                : '';

            return `
                <div class="row">
                    <div class="row-top">
                        <div>
                            <div class="row-title">${escapeHtml(description.title)}</div>
                            <div class="row-subtitle">${escapeHtml(formatAuditTimestamp(item.created_at))}</div>
                        </div>
                        <div class="audit-meta">
                            <span class="pill audit-pill ${escapeHtml(category.className)}">${escapeHtml(category.label)}</span>
                            <span class="pill">${escapeHtml(actor)}</span>
                            <span class="pill">${escapeHtml(entity)}</span>
                            ${item.request_id ? `<span class="pill">request ${escapeHtml(item.request_id)}</span>` : ''}
                        </div>
                    </div>
                    <div class="row-subtitle">IP: ${escapeHtml(item.ip_address || '-')} • UA: ${escapeHtml(item.user_agent || '-')}</div>
                    ${detailsHtml}
                    ${payloadHtml}
                </div>
            `;
        }

        function renderAuditEvents() {
            if (!cards.audit) {
                return;
            }

            const list = state.auditLoading
                ? '<div class="empty">Загружаем аудит...</div>'
                : state.auditError
                    ? `<div class="empty">${escapeHtml(state.auditError)}</div>`
                    : state.auditEvents.length
                        ? state.auditEvents.map((item) => renderAuditEventRow(item)).join('')
                        : '<div class="empty">За выбранный день событий не найдено</div>';

            cards.audit.innerHTML = `
                <div class="card-header">
                    <div>
                        <h3>Аудит действий</h3>
                        <p>Показываем все действия только за один выбранный день. По умолчанию открыт сегодняшний день.</p>
                    </div>
                    <div class="pill">${state.auditEvents.length} событий</div>
                </div>
                <div class="audit-toolbar">
                    <div class="field audit-date-input">
                        <label>День</label>
                        <input type="date" value="${escapeHtml(state.auditSelectedDate)}" data-audit-date-input="true">
                    </div>
                    <div class="row-actions">
                        <button class="ghost-button" type="button" data-audit-refresh="true">Обновить аудит</button>
                    </div>
                </div>
                <div class="audit-list">${list}</div>
            `;
        }

        function beginEdit(section, id) {
            const source = getSectionData(section).find((item) => getItemID(section, item) === id);
            state.editing[`${section}:${id}`] = structuredClone(source);
            renderAllCards();
        }

        function cancelEdit(section, id) {
            delete state.editing[`${section}:${id}`];
            renderAllCards();
        }

        function getSectionData(section) {
            switch (section) {
                case 'establishments':
                    return state.establishments;
                case 'orderMethods':
                    return state.orderMethods;
                case 'statuses':
                    return state.statuses;
                case 'currencies':
                    return state.currencies;
                default:
                    return [];
            }
        }

        function getItemID(section, item) {
            switch (section) {
                case 'establishments':
                    return item.establishment_id;
                case 'orderMethods':
                    return item.order_method_id;
                case 'statuses':
                    return item.status_id;
                case 'currencies':
                    return item.currency_id;
                default:
                    return null;
            }
        }

        function renderAllCards() {
            renderDashboardMenu();
            renderMessageSender();
            renderOrderCreate();
            renderInventoryCreate();
            renderProductRegistrationCreate();
            renderOrderManagement();
            renderContacts();
            renderPendingUsers();
            renderUsers();
            renderAuditEvents();
            renderProductImport();
            renderEstablishments();
            renderOrderMethods();
            renderStatuses();
            renderCurrencies();
            applyDashboardMenuVisibility();
        }

        function getStatusesByType(statusType) {
            return state.statuses.filter((item) => item.status_type === statusType);
        }

        function getDefaultCurrencyID() {
            const rub = state.currencies.find((item) => (item.currency_name || '').toUpperCase() === 'RUB');
            if (rub) {
                return rub.currency_id;
            }
            return state.currencies[0]?.currency_id || '';
        }

        function renderSelectOptions(items, getValue, getLabel, selectedValue = '') {
            return items.map((item) => {
                const value = getValue(item);
                const isSelected = String(value) === String(selectedValue);
                return `<option value="${escapeHtml(value)}"${isSelected ? ' selected' : ''}>${escapeHtml(getLabel(item))}</option>`;
            }).join('');
        }

        function renderChoiceButtons(items, getValue, getLabel, selectedValue = '', options = {}) {
            const { field, allowEmpty = false, emptyLabel = 'Без значения' } = options;
            const buttons = items.map((item) => {
                const value = String(getValue(item));
                const isSelected = String(selectedValue) === value;
                return `
                    <button
                        class="choice-button${isSelected ? ' active' : ''}"
                        type="button"
                        data-order-choice-field="${escapeHtml(field)}"
                        data-order-choice-value="${escapeHtml(value)}"
                    >${escapeHtml(getLabel(item))}</button>
                `;
            });

            if (allowEmpty) {
                buttons.unshift(`
                    <button
                        class="choice-button is-clear${!selectedValue ? ' active' : ''}"
                        type="button"
                        data-order-choice-field="${escapeHtml(field)}"
                        data-order-choice-value=""
                    >${escapeHtml(emptyLabel)}</button>
                `);
            }

            return buttons.join('');
        }

        function createOrderItemDraft() {
            return {
                key: createDraftKey('order-item'),
                product_id: '',
                product_article: '',
                product_name: '',
                item_quantity: '1',
                item_price: '0.00',
                item_currency_id: '',
                order_item_status_id: '',
                searchQuery: '',
                searchResults: [],
                selectedProduct: null,
                searchLoading: false,
                searchError: '',
                searchRequestSeq: 0,
                searchDebounceId: null,
            };
        }

        function createDraftKey(prefix) {
            return `${prefix}-${Math.random().toString(36).slice(2, 10)}`;
        }

        function formatDateTime(value) {
            if (!value) {
                return 'Дата не указана';
            }
            const date = new Date(value);
            if (Number.isNaN(date.getTime())) {
                return value;
            }
            return date.toLocaleString('ru-RU', {
                year: 'numeric',
                month: '2-digit',
                day: '2-digit',
                hour: '2-digit',
                minute: '2-digit',
            });
        }

        function createManagedOrderItemDraft(item = {}) {
            return {
                key: createDraftKey('managed-order-item'),
                product_id: String(item.order_item_product_id || ''),
                product_article: item.order_item_article || '',
                product_name: item.order_item_name || '',
                item_quantity: String(item.order_item_quantity || 1),
                item_price: String(item.order_item_price || '0.00'),
                item_currency_id: String(item.order_item_currency_id || getDefaultCurrencyID() || ''),
                order_item_status_id: String(item.order_item_status_id || ''),
                order_item_supplier: item.order_item_supplier || '',
                order_item_note: item.order_item_note || '',
                order_item_source_establishment_id: String(item.order_item_source_establishment_id || ''),
                order_item_destination_establishment_id: String(item.order_item_destination_establishment_id || ''),
                order_item_checkpoint_started: Boolean(item.order_item_checkpoint_started),
                order_item_checkpoint_completed: Boolean(item.order_item_checkpoint_completed),
            };
        }

        function createManagedOrderEditor(order) {
            const orderStatuses = getStatusesByType('orders');
            return {
                order_id: order.order_id,
                order_establishment_id: String(order.order_establishment_id || state.establishments[0]?.establishment_id || ''),
                order_method_id: String(order.order_method_id || state.orderMethods[0]?.order_method_id || ''),
                order_sub_method: order.order_sub_method || '',
                order_contact_method: order.order_contact_method || '',
                order_customer: order.order_customer || '',
                order_info: order.order_info || '',
                order_status_id: String(order.order_status_id || orderStatuses[0]?.status_id || ''),
                items: Array.isArray(order.items) && order.items.length
                    ? order.items.map((item) => createManagedOrderItemDraft(item))
                    : [createManagedOrderItemDraft()],
            };
        }

        function getManagedOrderEditor(orderID) {
            return state.orderManagement.editors[String(orderID)] || null;
        }

        function getManagedOrder(orderID) {
            return state.orderManagement.items.find((item) => Number(item.order_id) === Number(orderID)) || null;
        }

        function replaceManagedOrder(item) {
            state.orderManagement.items = state.orderManagement.items.map((entry) => Number(entry.order_id) === Number(item.order_id) ? item : entry);
            state.orders = state.orders.map((entry) => Number(entry.order_id) === Number(item.order_id) ? item : entry);
        }

        function updateManagedOrderStatusDraft(orderID, value) {
            state.orderManagement.statusDrafts[String(orderID)] = value;
        }

        function updateManagedOrderFilter(field, value) {
            state.orderManagement.filters[field] = value;
            renderOrderManagement();
        }

        function normalizeMatchValue(value) {
            return String(value || '')
                .toLowerCase()
                .replace(/\s+/g, ' ')
                .trim();
        }

        function parseImportedOrderRows(rawText) {
            return String(rawText || '')
                .split(/\r?\n/)
                .map((line) => line.trim())
                .filter(Boolean)
                .map((line) => {
                    const delimiter = line.includes('\t') ? '\t' : line.includes(';') ? ';' : ',';
                    const columns = line.split(delimiter).map((item) => item.trim());
                    const nomenclature = columns[0] || '';
                    const quantity = columns[1] || '1';
                    const price = columns[2] || '0.00';
                    return { nomenclature, quantity, price };
                })
                .filter((row) => row.nomenclature);
        }

        async function findProductByImportedNomenclature(nomenclature) {
            const query = String(nomenclature || '').trim();
            if (!query) {
                return null;
            }

            const params = new URLSearchParams({
                search: query,
                page: '1',
                page_size: '8',
                sort_by: 'product_name',
                sort_order: 'asc',
            });
            const payload = await request(`/products?${params.toString()}`, { method: 'GET' });
            const items = payload.items || [];
            const normalizedQuery = normalizeMatchValue(query);

            return items.find((item) => normalizeMatchValue(item.product_name) === normalizedQuery || normalizeMatchValue(item.product_article) === normalizedQuery)
                || items.find((item) => normalizeMatchValue(item.product_name).includes(normalizedQuery) || normalizeMatchValue(item.product_article).includes(normalizedQuery))
                || null;
        }

        async function importOrderRowsToDraft(rawText) {
            const rows = parseImportedOrderRows(rawText);
            if (!rows.length) {
                throw new Error('Вставь строки товаров: номенклатура, количество, цена');
            }

            state.orderImport.loading = true;
            state.orderImport.status = 'Ищем совпадения по каталогу и собираем позиции заказа...';
            state.orderImport.statusType = '';
            renderProductImport();

            const defaultCurrencyID = String(getDefaultCurrencyID() || '');
            const importedRows = [];

            for (const row of rows) {
                const matchedProduct = await findProductByImportedNomenclature(row.nomenclature);
                importedRows.push({
                    ...row,
                    matchedProduct,
                });
            }

            const nextItems = importedRows.map((row) => ({
                ...createOrderItemDraft(),
                product_id: row.matchedProduct ? String(row.matchedProduct.product_id || '') : '',
                product_article: row.matchedProduct?.product_article || '',
                product_name: row.matchedProduct?.product_name || row.nomenclature,
                item_quantity: String(Number(row.quantity) > 0 ? Number(row.quantity) : 1),
                item_price: String(row.price || '0.00').trim() || '0.00',
                item_currency_id: defaultCurrencyID,
                selectedProduct: row.matchedProduct || null,
                searchQuery: row.matchedProduct ? formatProductSearchLabel(row.matchedProduct) : row.nomenclature,
            }));

            ensureOrderDraftDefaults();
            state.orderDraft.items = nextItems.length ? nextItems : [createOrderItemDraft()];
            state.orderImport.rawText = rawText;
            state.orderImport.parsedRows = importedRows;
            state.orderImport.loading = false;
            const matchedCount = importedRows.filter((row) => row.matchedProduct).length;
            state.orderImport.status = `Импортировано строк: ${importedRows.length}. Совпадений по каталогу: ${matchedCount}.`;
            state.orderImport.statusType = matchedCount === importedRows.length ? 'ok' : '';
            renderOrderCreate();
            renderProductImport();
        }

        function updateContactsSearch(value) {
            state.contactsView.search = value;
            renderContacts();
        }

        function updateOrderImportRawText(value) {
            state.orderImport.rawText = value;
        }

        function updateManagedOrderEditorMeta(orderID, field, value) {
            const editor = getManagedOrderEditor(orderID);
            if (!editor) {
                return;
            }
            editor[field] = value;
        }

        function updateManagedOrderEditorItemField(orderID, itemKey, field, value) {
            const editor = getManagedOrderEditor(orderID);
            if (!editor) {
                return;
            }
            const item = editor.items.find((entry) => entry.key === itemKey);
            if (!item) {
                return;
            }
            item[field] = value;
        }

        function addManagedOrderEditorItem(orderID) {
            const editor = getManagedOrderEditor(orderID);
            if (!editor) {
                return;
            }
            editor.items.push(createManagedOrderItemDraft());
            renderOrderManagement();
        }

        function removeManagedOrderEditorItem(orderID, itemKey) {
            const editor = getManagedOrderEditor(orderID);
            if (!editor || editor.items.length <= 1) {
                return;
            }
            editor.items = editor.items.filter((item) => item.key !== itemKey);
            renderOrderManagement();
        }

        function getFilteredManagedOrders() {
            const search = String(state.orderManagement.filters.search || '').trim().toLowerCase();
            return state.orderManagement.items.filter((order) => {
                if (state.orderManagement.filters.establishment_id && String(order.order_establishment_id) !== String(state.orderManagement.filters.establishment_id)) {
                    return false;
                }
                if (state.orderManagement.filters.method_id && String(order.order_method_id) !== String(state.orderManagement.filters.method_id)) {
                    return false;
                }
                if (state.orderManagement.filters.status_id && String(order.order_status_id) !== String(state.orderManagement.filters.status_id)) {
                    return false;
                }
                if (!search) {
                    return true;
                }
                const haystack = [
                    order.order_id,
                    order.order_customer,
                    order.order_info,
                    order.order_status,
                    order.order_establishment_name,
                    order.order_method_name,
                    ...(Array.isArray(order.items) ? order.items.flatMap((item) => [item.order_item_name, item.order_item_article, item.order_item_note]) : []),
                ].join(' ').toLowerCase();
                return haystack.includes(search);
            });
        }

        async function loadOrderManagementPage({ page = 1, silent = false } = {}) {
            state.orderManagement.loading = true;
            state.orderManagement.pagination.page = page;
            if (!silent) {
                renderOrderManagement();
            }

            try {
                const payload = await request(`/orders?page=${page}&page_size=50`, { method: 'GET' });
                state.orderManagement.items = payload.items || [];
                state.orderManagement.pagination = payload.pagination || { page, page_size: 50, total: 0, total_pages: 0 };
            } finally {
                state.orderManagement.loading = false;
                renderOrderManagement();
            }
        }

        async function loadContactsPage({ page = 1, silent = false } = {}) {
            state.contactsView.loading = true;
            state.contactsView.pagination.page = page;
            if (!silent) {
                renderContacts();
            }

            const params = new URLSearchParams({
                contact_type: state.contactsView.type,
                page: String(page),
                page_size: '50',
            });

            if (String(state.contactsView.search || '').trim()) {
                params.set('search', String(state.contactsView.search || '').trim());
            }

            try {
                const payload = await request(`/contacts?${params.toString()}`, { method: 'GET' });
                state.contactsView.items = payload.items || [];
                state.contactsView.pagination = payload.pagination || { page, page_size: 50, total: 0, total_pages: 0 };
            } finally {
                state.contactsView.loading = false;
                renderContacts();
            }
        }

        async function toggleManagedOrderEditor(orderID) {
            const normalizedID = String(orderID);
            if (String(state.orderManagement.expandedOrderID || '') === normalizedID) {
                state.orderManagement.expandedOrderID = null;
                renderOrderManagement();
                return;
            }

            state.orderManagement.expandedOrderID = normalizedID;
            state.orderManagement.loadingOrderID = normalizedID;
            renderOrderManagement();

            try {
                const payload = await request(`/orders/${orderID}`, { method: 'GET' });
                state.orderManagement.editors[normalizedID] = createManagedOrderEditor(payload.item || {});
            } finally {
                state.orderManagement.loadingOrderID = null;
                renderOrderManagement();
            }
        }

        async function saveManagedOrderStatus(orderID) {
            const order = getManagedOrder(orderID);
            const statusID = state.orderManagement.statusDrafts[String(orderID)] || String(order?.order_status_id || '');
            if (!statusID) {
                throw new Error('Для заказа нужно выбрать статус');
            }

            await request(`/orders/${orderID}/status`, {
                method: 'PUT',
                body: JSON.stringify({ order_status_id: Number(statusID) }),
            });

            await Promise.all([
                loadDashboardData(),
                loadOrderManagementPage({ page: state.orderManagement.pagination.page || 1, silent: true }),
            ]);
        }

        function buildManagedOrderUpdatePayload(orderID) {
            const editor = getManagedOrderEditor(orderID);
            if (!editor) {
                throw new Error('Редактор заказа не инициализирован');
            }

            return {
                order_establishment_id: Number(editor.order_establishment_id),
                order_method_id: Number(editor.order_method_id),
                order_sub_method: String(editor.order_sub_method || '').trim() || null,
                order_contact_method: String(editor.order_contact_method || '').trim() || null,
                order_customer: String(editor.order_customer || '').trim(),
                order_info: String(editor.order_info || '').trim(),
                order_status_id: Number(editor.order_status_id),
                items: editor.items.map((item) => ({
                    product_id: item.product_id ? Number(item.product_id) : null,
                    product_article: String(item.product_article || '').trim(),
                    product_name: String(item.product_name || '').trim(),
                    order_item_quantity: Number(item.item_quantity || 1),
                    order_item_price: String(item.item_price || '0.00').trim() || '0.00',
                    order_item_status_id: item.order_item_status_id ? Number(item.order_item_status_id) : null,
                    order_item_supplier: String(item.order_item_supplier || '').trim() || null,
                    order_item_note: String(item.order_item_note || '').trim() || null,
                    order_item_source_establishment_id: item.order_item_source_establishment_id ? Number(item.order_item_source_establishment_id) : null,
                    order_item_destination_establishment_id: item.order_item_destination_establishment_id ? Number(item.order_item_destination_establishment_id) : null,
                    order_item_currency_id: item.item_currency_id ? Number(item.item_currency_id) : null,
                    order_item_checkpoint_started: Boolean(item.order_item_checkpoint_started),
                    order_item_checkpoint_completed: Boolean(item.order_item_checkpoint_completed),
                })),
            };
        }

        async function saveManagedOrder(orderID) {
            const normalizedID = String(orderID);
            state.orderManagement.savingOrderID = normalizedID;
            renderOrderManagement();

            try {
                const payload = await request(`/orders/${orderID}`, {
                    method: 'PUT',
                    body: JSON.stringify(buildManagedOrderUpdatePayload(orderID)),
                });
                state.orderManagement.editors[normalizedID] = createManagedOrderEditor(payload.item || {});
                state.orderManagement.expandedOrderID = normalizedID;
                await Promise.all([
                    loadDashboardData(),
                    loadOrderManagementPage({ page: state.orderManagement.pagination.page || 1, silent: true }),
                ]);
            } finally {
                state.orderManagement.savingOrderID = null;
                renderOrderManagement();
            }
        }

        function renderManagedOrderEditorItem(orderID, item, index, orderItemStatuses) {
            return `
                <div class="order-editor-item">
                    <div class="order-editor-item-head">
                        <div>
                            <div class="row-title">Позиция ${index + 1}</div>
                            <div class="row-subtitle">Можно менять статус, данные товара, заметку и стоимость.</div>
                        </div>
                        ${getManagedOrderEditor(orderID)?.items.length > 1 ? `<button class="ghost-button" type="button" data-managed-order-remove-item="${escapeHtml(item.key)}" data-order-id="${escapeHtml(orderID)}">Удалить</button>` : ''}
                    </div>
                    <div class="order-editor-grid">
                        <div class="field" data-span="2"><label>Артикул</label><input data-managed-order-item-field="product_article" data-order-id="${escapeHtml(orderID)}" data-item-key="${escapeHtml(item.key)}" value="${escapeHtml(item.product_article)}"></div>
                        <div class="field" data-span="3"><label>Название</label><input data-managed-order-item-field="product_name" data-order-id="${escapeHtml(orderID)}" data-item-key="${escapeHtml(item.key)}" value="${escapeHtml(item.product_name)}"></div>
                        <div class="field"><label>Product ID</label><input data-managed-order-item-field="product_id" data-order-id="${escapeHtml(orderID)}" data-item-key="${escapeHtml(item.key)}" value="${escapeHtml(item.product_id)}" placeholder="необязательно"></div>
                        <div class="field"><label>Кол-во</label><input type="number" min="1" data-managed-order-item-field="item_quantity" data-order-id="${escapeHtml(orderID)}" data-item-key="${escapeHtml(item.key)}" value="${escapeHtml(item.item_quantity)}"></div>
                        <div class="field"><label>Цена</label><input type="number" min="0" step="0.01" data-managed-order-item-field="item_price" data-order-id="${escapeHtml(orderID)}" data-item-key="${escapeHtml(item.key)}" value="${escapeHtml(item.item_price)}"></div>
                        <div class="field"><label>Валюта</label><select data-managed-order-item-field="item_currency_id" data-order-id="${escapeHtml(orderID)}" data-item-key="${escapeHtml(item.key)}">${renderSelectOptions(state.currencies, (currency) => currency.currency_id, (currency) => `${currency.currency_name}${currency.currency_sign ? ` (${currency.currency_sign})` : ''}`, item.item_currency_id)}</select></div>
                        <div class="field" data-span="2"><label>Статус позиции</label><select data-managed-order-item-field="order_item_status_id" data-order-id="${escapeHtml(orderID)}" data-item-key="${escapeHtml(item.key)}"><option value="">Без статуса</option>${renderSelectOptions(orderItemStatuses, (status) => status.status_id, (status) => status.status_status, item.order_item_status_id)}</select></div>
                        <div class="field" data-span="2"><label>Поставщик</label><input data-managed-order-item-field="order_item_supplier" data-order-id="${escapeHtml(orderID)}" data-item-key="${escapeHtml(item.key)}" value="${escapeHtml(item.order_item_supplier)}"></div>
                        <div class="field" data-span="2"><label>Заметка</label><input data-managed-order-item-field="order_item_note" data-order-id="${escapeHtml(orderID)}" data-item-key="${escapeHtml(item.key)}" value="${escapeHtml(item.order_item_note)}"></div>
                    </div>
                </div>
            `;
        }

        function renderManagedOrderEditor(orderID) {
            if (String(state.orderManagement.loadingOrderID || '') === String(orderID)) {
                return '<div class="order-editor"><div class="empty">Загружаем полную карточку заказа...</div></div>';
            }

            const editor = getManagedOrderEditor(orderID);
            if (!editor) {
                return '<div class="order-editor"><div class="empty">Не удалось открыть заказ для редактирования</div></div>';
            }

            const orderStatuses = getStatusesByType('orders');
            const orderItemStatuses = getStatusesByType('order_products');
            const isSaving = String(state.orderManagement.savingOrderID || '') === String(orderID);

            return `
                <div class="order-editor">
                    <div class="form-grid">
                        <div class="field"><label>Точка</label><select data-managed-order-meta="order_establishment_id" data-order-id="${escapeHtml(orderID)}">${renderSelectOptions(state.establishments, (item) => item.establishment_id, (item) => item.establishment_name, editor.order_establishment_id)}</select></div>
                        <div class="field"><label>Метод</label><select data-managed-order-meta="order_method_id" data-order-id="${escapeHtml(orderID)}">${renderSelectOptions(state.orderMethods, (item) => item.order_method_id, (item) => item.order_method_name, editor.order_method_id)}</select></div>
                        <div class="field"><label>Подметод</label><input data-managed-order-meta="order_sub_method" data-order-id="${escapeHtml(orderID)}" value="${escapeHtml(editor.order_sub_method)}"></div>
                        <div class="field"><label>Способ связи</label><select data-managed-order-meta="order_contact_method" data-order-id="${escapeHtml(orderID)}"><option value=""${editor.order_contact_method ? '' : ' selected'}>Не указан</option>${renderSelectOptions(ORDER_CONTACT_METHODS, (item) => item, (item) => item, editor.order_contact_method)}</select></div>
                        <div class="field"><label>Статус заказа</label><select data-managed-order-meta="order_status_id" data-order-id="${escapeHtml(orderID)}">${renderSelectOptions(orderStatuses, (item) => item.status_id, (item) => item.status_status, editor.order_status_id)}</select></div>
                        <div class="field"><label>Покупатель</label><input data-managed-order-meta="order_customer" data-order-id="${escapeHtml(orderID)}" value="${escapeHtml(editor.order_customer)}"></div>
                        <div class="field field-wide"><label>Информация / адрес</label><input data-managed-order-meta="order_info" data-order-id="${escapeHtml(orderID)}" value="${escapeHtml(editor.order_info)}"></div>
                    </div>
                    <div class="order-editor-items">${editor.items.map((item, index) => renderManagedOrderEditorItem(orderID, item, index, orderItemStatuses)).join('')}</div>
                    <div class="row-actions">
                        <button class="ghost-button" type="button" data-managed-order-add-item="true" data-order-id="${escapeHtml(orderID)}">Добавить товар</button>
                        <button class="button" type="button" data-managed-order-save="${escapeHtml(orderID)}" ${isSaving ? 'disabled' : ''}>${isSaving ? 'Сохраняем...' : 'Сохранить заказ'}</button>
                        <button class="ghost-button" type="button" data-managed-order-toggle-edit="${escapeHtml(orderID)}">Свернуть</button>
                    </div>
                </div>
            `;
        }

        function renderManagedOrderRow(order) {
            const currentStatusID = state.orderManagement.statusDrafts[String(order.order_id)] || String(order.order_status_id || '');
            const isExpanded = String(state.orderManagement.expandedOrderID || '') === String(order.order_id);
            const itemSummary = Array.isArray(order.items) && order.items.length
                ? order.items.slice(0, 3).map((item) => `${item.order_item_article || '-'} / ${item.order_item_name || 'Без названия'}`).join('<br>')
                : 'Без позиций';

            return `
                <tr>
                    <td>
                        <div class="table-cell-stack">
                            <div class="table-title">#${escapeHtml(order.order_id)}</div>
                            <div class="table-subtitle">${escapeHtml(formatDateTime(order.order_created_at))}</div>
                        </div>
                    </td>
                    <td>
                        <div class="table-cell-stack">
                            <div class="table-title">${escapeHtml(order.order_establishment_name || '-')}</div>
                            <div class="table-subtitle">${escapeHtml(order.order_method_name || '-')} ${order.order_sub_method ? `• ${escapeHtml(order.order_sub_method)}` : ''}</div>
                        </div>
                    </td>
                    <td>
                        ${order.order_contact_method ? `<span class="pill">${escapeHtml(order.order_contact_method)}</span>` : '<div class="table-subtitle">—</div>'}
                    </td>
                    <td>
                        <div class="table-cell-stack">
                            <div class="table-title">${escapeHtml(order.order_customer || 'Без покупателя')}</div>
                            <div class="table-subtitle">${escapeHtml(order.order_info || 'Без адреса')}</div>
                        </div>
                    </td>
                    <td><div class="table-subtitle">${itemSummary}</div></td>
                    <td>
                        <div class="table-cell-stack">
                            <select data-managed-order-status-select="${escapeHtml(order.order_id)}">${renderSelectOptions(getStatusesByType('orders'), (status) => status.status_id, (status) => status.status_status, currentStatusID)}</select>
                            <button class="ghost-button" type="button" data-managed-order-save-status="${escapeHtml(order.order_id)}">Сменить статус</button>
                        </div>
                    </td>
                    <td>
                        <div class="table-cell-stack">
                            <div class="table-title">${escapeHtml(Array.isArray(order.items) ? order.items.length : 0)}</div>
                            <div class="table-subtitle">${escapeHtml(order.order_status || 'Без статуса')}</div>
                        </div>
                    </td>
                    <td>
                        <div class="row-actions">
                            <button class="ghost-button" type="button" data-managed-order-toggle-edit="${escapeHtml(order.order_id)}">${isExpanded ? 'Свернуть' : 'Редактировать'}</button>
                        </div>
                    </td>
                </tr>
                ${isExpanded ? `<tr class="orders-editor-row"><td colspan="8">${renderManagedOrderEditor(order.order_id)}</td></tr>` : ''}
            `;
        }

        function renderOrderManagement() {
            const items = getFilteredManagedOrders();
            const pagination = state.orderManagement.pagination || { page: 1, total_pages: 0, total: 0 };

            cards.orderManagement.innerHTML = `
                <div class="card-header">
                    <div>
                        <h3>Все заказы</h3>
                        <p>Фильтры собраны в одну строку, таблица показывает до 50 заказов на страницу, а расширенная строка позволяет менять заказ и его позиции.</p>
                    </div>
                    <div class="pill">${escapeHtml(pagination.total || 0)} total</div>
                </div>
                <div class="filters-row">
                    <div class="field"><label>Поиск по странице</label><input data-managed-orders-filter="search" value="${escapeHtml(state.orderManagement.filters.search)}" placeholder="ID, покупатель, адрес, товар"></div>
                    <div class="field"><label>Точка</label><select data-managed-orders-filter="establishment_id"><option value="">Все точки</option>${renderSelectOptions(state.establishments, (item) => item.establishment_id, (item) => item.establishment_name, state.orderManagement.filters.establishment_id)}</select></div>
                    <div class="field"><label>Метод</label><select data-managed-orders-filter="method_id"><option value="">Все методы</option>${renderSelectOptions(state.orderMethods, (item) => item.order_method_id, (item) => item.order_method_name, state.orderManagement.filters.method_id)}</select></div>
                    <div class="field"><label>Статус</label><select data-managed-orders-filter="status_id"><option value="">Все статусы</option>${renderSelectOptions(getStatusesByType('orders'), (item) => item.status_id, (item) => item.status_status, state.orderManagement.filters.status_id)}</select></div>
                    <div class="row-actions"><button class="ghost-button" type="button" data-managed-orders-reload="true">Обновить страницу</button></div>
                </div>
                <div class="orders-table-wrap">
                    <table class="orders-table">
                        <thead>
                            <tr>
                                <th>ID</th>
                                <th>Точка / метод</th>
                                <th>Связь</th>
                                <th>Покупатель</th>
                                <th>Позиции</th>
                                <th>Статус</th>
                                <th>Итог</th>
                                <th>Действия</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${state.orderManagement.loading && !state.orderManagement.items.length ? '<tr><td colspan="8"><div class="empty">Загружаем заказы...</div></td></tr>' : ''}
                            ${!state.orderManagement.loading && !items.length ? '<tr><td colspan="8"><div class="empty">На этой странице нет заказов под выбранные фильтры</div></td></tr>' : ''}
                            ${items.map((order) => renderManagedOrderRow(order)).join('')}
                        </tbody>
                    </table>
                </div>
                <div class="pagination-bar">
                    <div class="pagination-meta">Страница ${escapeHtml(pagination.page || 1)} из ${escapeHtml(pagination.total_pages || 1)}. Загружено ${escapeHtml(items.length)} заказов из ${escapeHtml(state.orderManagement.items.length)} на текущей странице.</div>
                    <div class="row-actions">
                        <button class="ghost-button" type="button" data-managed-orders-page="${escapeHtml((pagination.page || 1) - 1)}" ${pagination.page <= 1 ? 'disabled' : ''}>Назад</button>
                        <button class="ghost-button" type="button" data-managed-orders-page="${escapeHtml((pagination.page || 1) + 1)}" ${(pagination.page || 1) >= (pagination.total_pages || 1) ? 'disabled' : ''}>Дальше</button>
                    </div>
                </div>
            `;
        }

        function renderContactCard(item) {
            return `
                <div class="contact-card">
                    <div>
                        <div class="row-title">${escapeHtml(item.contact_name || 'Без имени')}</div>
                        <div class="row-subtitle">${escapeHtml(item.contact_info || 'Контактная информация не заполнена')}</div>
                    </div>
                    <div class="contact-meta">
                        ${item.contact_establishment_name ? `<span class="pill">${escapeHtml(item.contact_establishment_name)}</span>` : ''}
                        ${item.contact_order_method_name ? `<span class="pill">${escapeHtml(item.contact_order_method_name)}</span>` : ''}
                        ${item.contact_order_sub_method ? `<span class="pill">${escapeHtml(item.contact_order_sub_method)}</span>` : ''}
                    </div>
                    <div class="row-subtitle">Создан: ${escapeHtml(formatDateTime(item.contact_created_at))}${item.contact_owner_user_login ? ` • @${escapeHtml(item.contact_owner_user_login)}` : ''}</div>
                </div>
            `;
        }

        function renderContacts() {
            const pagination = state.contactsView.pagination || { page: 1, total_pages: 0, total: 0 };

            cards.contacts.innerHTML = `
                <div class="card-header">
                    <div>
                        <h3>Контрагенты</h3>
                        <p>Сводный реестр покупателей и поставщиков, которые появились из заказов и приходных документов.</p>
                    </div>
                    <div class="pill">${escapeHtml(pagination.total || 0)} total</div>
                </div>
                <div class="row-top">
                    <div class="segmented">
                        <button class="segmented-button${state.contactsView.type === 'buyer' ? ' active' : ''}" type="button" data-contacts-type="buyer">Покупатели</button>
                        <button class="segmented-button${state.contactsView.type === 'supplier' ? ' active' : ''}" type="button" data-contacts-type="supplier">Поставщики</button>
                    </div>
                    <div class="row-actions">
                        <div class="field" style="margin: 0; min-width: 260px;"><label>Поиск</label><input data-contacts-search="true" value="${escapeHtml(state.contactsView.search)}" placeholder="Имя, адрес, комментарий"></div>
                        <button class="ghost-button" type="button" data-contacts-search-submit="true">Найти</button>
                    </div>
                </div>
                <div class="contact-grid">
                    ${state.contactsView.loading && !state.contactsView.items.length ? '<div class="empty">Загружаем контрагентов...</div>' : ''}
                    ${!state.contactsView.loading && !state.contactsView.items.length ? '<div class="empty">Список пуст</div>' : ''}
                    ${state.contactsView.items.map((item) => renderContactCard(item)).join('')}
                </div>
                <div class="pagination-bar">
                    <div class="pagination-meta">Страница ${escapeHtml(pagination.page || 1)} из ${escapeHtml(pagination.total_pages || 1)}.</div>
                    <div class="row-actions">
                        <button class="ghost-button" type="button" data-contacts-page="${escapeHtml((pagination.page || 1) - 1)}" ${pagination.page <= 1 ? 'disabled' : ''}>Назад</button>
                        <button class="ghost-button" type="button" data-contacts-page="${escapeHtml((pagination.page || 1) + 1)}" ${(pagination.page || 1) >= (pagination.total_pages || 1) ? 'disabled' : ''}>Дальше</button>
                    </div>
                </div>
            `;
        }

        function createSingleProductSearchState() {
            return {
                query: '',
                results: [],
                selectedProduct: null,
                loading: false,
                error: '',
                requestSeq: 0,
                debounceId: null,
            };
        }

        function clearSearchDebounce(searchState) {
            if (searchState?.debounceId) {
                window.clearTimeout(searchState.debounceId);
                searchState.debounceId = null;
            }
        }

        function resetOrderDraft() {
            if (state.orderDraft?.items) {
                state.orderDraft.items.forEach((item) => clearSearchDebounce(item));
            }

            state.orderDraft = {
                order_establishment_id: '',
                order_method_id: '',
                order_sub_method: '',
                order_contact_method: '',
                order_customer: '',
                message_text: '',
                order_info: '',
                order_status_id: '',
                items: [createOrderItemDraft()],
            };
        }

        function ensureOrderDraftDefaults() {
            if (!state.orderDraft.items.length) {
                state.orderDraft.items = [createOrderItemDraft()];
            }

            if (!state.orderDraft.order_establishment_id && state.establishments[0]?.establishment_id) {
                state.orderDraft.order_establishment_id = String(state.establishments[0].establishment_id);
            }

            if (!state.orderDraft.order_method_id && state.orderMethods[0]?.order_method_id) {
                state.orderDraft.order_method_id = String(state.orderMethods[0].order_method_id);
            }

            const defaultCurrencyID = String(getDefaultCurrencyID() || '');
            state.orderDraft.items.forEach((item) => {
                if (!item.item_currency_id && defaultCurrencyID) {
                    item.item_currency_id = defaultCurrencyID;
                }
            });
        }

        function getOrderItemDraft(itemKey) {
            return state.orderDraft.items.find((item) => item.key === itemKey) || null;
        }

        function getSingleProductSearchState(section) {
            switch (section) {
                case 'inventory':
                    return state.inventoryProductSearch;
                case 'productRegistration':
                    return state.productRegistrationProductSearch;
                default:
                    return null;
            }
        }

        function getSingleDocumentForm(section) {
            switch (section) {
                case 'inventory':
                    return cards.inventoryCreate.querySelector('form[data-document-form="inventory"]');
                case 'productRegistration':
                    return cards.productRegistrationCreate.querySelector('form[data-document-form="productRegistration"]');
                default:
                    return null;
            }
        }

        function resetSingleDocumentProductSearch(section, clearFields = false) {
            const searchState = getSingleProductSearchState(section);
            if (!searchState) {
                return;
            }

            clearSearchDebounce(searchState);
            searchState.query = '';
            searchState.results = [];
            searchState.selectedProduct = null;
            searchState.loading = false;
            searchState.error = '';
            searchState.requestSeq += 1;

            const form = getSingleDocumentForm(section);
            if (form && clearFields) {
                const fieldsToClear = ['product_id', 'product_article', 'product_name', 'product_search'];
                fieldsToClear.forEach((fieldName) => {
                    const input = form.querySelector(`[name="${fieldName}"]`);
                    if (input) {
                        input.value = '';
                    }
                });
            }
        }

        function formatProductSearchLabel(product) {
            if (!product) {
                return '';
            }
            const article = product.product_article || 'Без артикула';
            const name = product.product_name || 'Без названия';
            return `${article} - ${name}`;
        }

        function renderSingleDocumentProductSearchUI(section) {
            const searchState = getSingleProductSearchState(section);
            const form = getSingleDocumentForm(section);
            if (!searchState || !form) {
                return;
            }

            const searchInput = form.querySelector(`[data-single-product-search-input="${section}"]`);
            const meta = form.querySelector(`[data-single-product-meta="${section}"]`);
            const summary = form.querySelector(`[data-single-product-summary="${section}"]`);
            const results = form.querySelector(`[data-single-product-results="${section}"]`);
            const productIdInput = form.querySelector('input[name="product_id"]');
            const articleInput = form.querySelector('input[name="product_article"]');
            const nameInput = form.querySelector('input[name="product_name"]');

            if (!searchInput || !meta || !summary || !results || !productIdInput || !articleInput || !nameInput) {
                return;
            }

            const query = String(searchState.query || '').trim();
            const selected = searchState.selectedProduct;
            let metaText = 'Введи минимум 2 символа: можно искать по артикулу и по названию.';

            if (searchState.error) {
                metaText = searchState.error;
            } else if (searchState.loading) {
                metaText = 'Ищем товары в каталоге...';
            } else if (selected) {
                metaText = 'Товар выбран. Поля артикула и названия подставлены автоматически.';
            } else if (query.length >= 2 && !searchState.results.length) {
                metaText = 'По запросу ничего не найдено. Можно ввести товар вручную.';
            } else if (query.length >= 2) {
                metaText = `Найдено: ${searchState.results.length}`;
            }

            meta.className = `product-search-meta${searchState.error ? ' error' : ''}`;
            meta.textContent = metaText;

            if (selected) {
                productIdInput.value = String(selected.product_id || '');
                articleInput.value = selected.product_article || '';
                nameInput.value = selected.product_name || '';
                if (document.activeElement !== searchInput) {
                    searchInput.value = formatProductSearchLabel(selected);
                }

                summary.innerHTML = `
                    <div class="product-search-summary">
                        <div>
                            <strong>${escapeHtml(formatProductSearchLabel(selected))}</strong>
                            <span>${selected.product_cost_usd != null ? `Каталог: ${escapeHtml(selected.product_cost_usd)} USD` : 'Цена в каталоге не заполнена'}</span>
                        </div>
                        <button class="ghost-button" type="button" data-single-product-clear="${section}">Сбросить</button>
                    </div>
                `;
            } else {
                productIdInput.value = '';
                if (document.activeElement !== searchInput) {
                    searchInput.value = searchState.query;
                }
                summary.innerHTML = '';
            }

            if (!selected && query.length >= 2) {
                results.innerHTML = searchState.results.map((product) => `
                    <button class="product-search-item" type="button" data-single-product-select="${section}" data-product-id="${escapeHtml(product.product_id)}">
                        <span class="product-search-primary">${escapeHtml(product.product_name || 'Без названия')}</span>
                        <span class="product-search-secondary">Артикул: ${escapeHtml(product.product_article || '-')} • ID: ${escapeHtml(product.product_id || '-')}</span>
                    </button>
                `).join('');
            } else {
                results.innerHTML = '';
            }
        }

        async function performSingleDocumentProductSearch(section, query, requestSeq) {
            const searchState = getSingleProductSearchState(section);
            if (!searchState) {
                return;
            }

            try {
                const params = new URLSearchParams({
                    search: query,
                    page: '1',
                    page_size: '8',
                    sort_by: 'product_name',
                    sort_order: 'asc',
                });
                const payload = await request(`/products?${params.toString()}`, { method: 'GET' });
                if (requestSeq !== searchState.requestSeq) {
                    return;
                }
                searchState.results = payload.items || [];
                searchState.error = '';
            } catch (error) {
                if (requestSeq !== searchState.requestSeq) {
                    return;
                }
                searchState.results = [];
                searchState.error = error.message;
            } finally {
                if (requestSeq === searchState.requestSeq) {
                    searchState.loading = false;
                    renderSingleDocumentProductSearchUI(section);
                }
            }
        }

        function scheduleSingleDocumentProductSearch(section, rawQuery) {
            const searchState = getSingleProductSearchState(section);
            if (!searchState) {
                return;
            }

            const query = String(rawQuery || '').trim();
            searchState.query = rawQuery;
            searchState.error = '';
            clearSearchDebounce(searchState);

            if (searchState.selectedProduct && query !== formatProductSearchLabel(searchState.selectedProduct)) {
                searchState.selectedProduct = null;
            }

            if (query.length < 2) {
                searchState.results = [];
                searchState.loading = false;
                renderSingleDocumentProductSearchUI(section);
                return;
            }

            searchState.loading = true;
            searchState.results = [];
            const requestSeq = ++searchState.requestSeq;
            renderSingleDocumentProductSearchUI(section);
            searchState.debounceId = window.setTimeout(() => {
                performSingleDocumentProductSearch(section, query, requestSeq);
            }, 180);
        }

        function selectSingleDocumentProduct(section, productId) {
            const searchState = getSingleProductSearchState(section);
            if (!searchState) {
                return;
            }

            const product = searchState.results.find((item) => String(item.product_id) === String(productId));
            if (!product) {
                return;
            }

            searchState.selectedProduct = product;
            searchState.query = formatProductSearchLabel(product);
            searchState.results = [];
            searchState.loading = false;
            searchState.error = '';
            renderSingleDocumentProductSearchUI(section);
        }

        function getOrderItemRow(itemKey) {
            return cards.orderCreate.querySelector(`[data-order-item-row="${itemKey}"]`);
        }

        function renderOrderItemSearchUI(itemKey) {
            const item = getOrderItemDraft(itemKey);
            const row = getOrderItemRow(itemKey);
            if (!item || !row) {
                return;
            }

            const searchInput = row.querySelector(`[data-order-item-search-input="${itemKey}"]`);
            const meta = row.querySelector(`[data-order-item-meta="${itemKey}"]`);
            const summary = row.querySelector(`[data-order-item-summary="${itemKey}"]`);
            const results = row.querySelector(`[data-order-item-results="${itemKey}"]`);
            const productIdInput = row.querySelector('[data-order-item-field="product_id"]');
            const articleInput = row.querySelector('[data-order-item-field="product_article"]');
            const nameInput = row.querySelector('[data-order-item-field="product_name"]');
            if (!searchInput || !meta || !summary || !results || !productIdInput || !articleInput || !nameInput) {
                return;
            }

            const query = String(item.searchQuery || '').trim();
            const selected = item.selectedProduct;
            let metaText = 'Введи минимум 2 символа: поиск идёт по артикулу и названию товара.';

            if (item.searchError) {
                metaText = item.searchError;
            } else if (item.searchLoading) {
                metaText = 'Ищем товары в каталоге...';
            } else if (selected) {
                metaText = 'Товар выбран. Поля артикула и названия синхронизированы с каталогом.';
            } else if (query.length >= 2 && !item.searchResults.length) {
                metaText = 'Ничего не найдено. Можно ввести артикул и название вручную.';
            } else if (query.length >= 2) {
                metaText = `Найдено: ${item.searchResults.length}`;
            }

            meta.className = `product-search-meta${item.searchError ? ' error' : ''}`;
            meta.textContent = metaText;

            if (selected) {
                item.product_id = String(selected.product_id || '');
                item.product_article = selected.product_article || '';
                item.product_name = selected.product_name || '';
                productIdInput.value = item.product_id;
                articleInput.value = item.product_article;
                nameInput.value = item.product_name;
                if (document.activeElement !== searchInput) {
                    searchInput.value = formatProductSearchLabel(selected);
                }
                summary.innerHTML = `
                    <div class="product-search-summary">
                        <div>
                            <strong>${escapeHtml(formatProductSearchLabel(selected))}</strong>
                            <span>${selected.product_cost_usd != null ? `Каталог: ${escapeHtml(selected.product_cost_usd)} USD` : 'Цена в каталоге не заполнена'}</span>
                        </div>
                        <button class="ghost-button" type="button" data-order-item-clear-product="${escapeHtml(item.key)}">Сбросить</button>
                    </div>
                `;
            } else {
                item.product_id = '';
                productIdInput.value = '';
                if (document.activeElement !== searchInput) {
                    searchInput.value = item.searchQuery;
                }
                summary.innerHTML = '';
            }

            if (!selected && query.length >= 2) {
                results.innerHTML = item.searchResults.map((product) => `
                    <button class="product-search-item" type="button" data-order-item-select-product="${escapeHtml(item.key)}" data-product-id="${escapeHtml(product.product_id)}">
                        <span class="product-search-primary">${escapeHtml(product.product_name || 'Без названия')}</span>
                        <span class="product-search-secondary">Артикул: ${escapeHtml(product.product_article || '-')} • ID: ${escapeHtml(product.product_id || '-')}</span>
                    </button>
                `).join('');
            } else {
                results.innerHTML = '';
            }
        }

        async function performOrderItemProductSearch(itemKey, query, requestSeq) {
            const item = getOrderItemDraft(itemKey);
            if (!item) {
                return;
            }

            try {
                const params = new URLSearchParams({
                    search: query,
                    page: '1',
                    page_size: '8',
                    sort_by: 'product_name',
                    sort_order: 'asc',
                });
                const payload = await request(`/products?${params.toString()}`, { method: 'GET' });
                if (!getOrderItemDraft(itemKey) || requestSeq !== item.searchRequestSeq) {
                    return;
                }
                item.searchResults = payload.items || [];
                item.searchError = '';
            } catch (error) {
                if (!getOrderItemDraft(itemKey) || requestSeq !== item.searchRequestSeq) {
                    return;
                }
                item.searchResults = [];
                item.searchError = error.message;
            } finally {
                if (getOrderItemDraft(itemKey) && requestSeq === item.searchRequestSeq) {
                    item.searchLoading = false;
                    renderOrderItemSearchUI(itemKey);
                }
            }
        }

        function scheduleOrderItemProductSearch(itemKey, rawQuery) {
            const item = getOrderItemDraft(itemKey);
            if (!item) {
                return;
            }

            const query = String(rawQuery || '').trim();
            item.searchQuery = rawQuery;
            item.searchError = '';
            clearSearchDebounce(item);

            if (item.selectedProduct && query !== formatProductSearchLabel(item.selectedProduct)) {
                item.selectedProduct = null;
            }

            if (query.length < 2) {
                item.searchResults = [];
                item.searchLoading = false;
                renderOrderItemSearchUI(itemKey);
                return;
            }

            item.searchLoading = true;
            item.searchResults = [];
            const requestSeq = ++item.searchRequestSeq;
            renderOrderItemSearchUI(itemKey);
            item.searchDebounceId = window.setTimeout(() => {
                performOrderItemProductSearch(itemKey, query, requestSeq);
            }, 180);
        }

        function selectOrderItemProduct(itemKey, productId) {
            const item = getOrderItemDraft(itemKey);
            if (!item) {
                return;
            }

            const product = item.searchResults.find((entry) => String(entry.product_id) === String(productId));
            if (!product) {
                return;
            }

            item.selectedProduct = product;
            item.searchQuery = formatProductSearchLabel(product);
            item.searchResults = [];
            item.searchLoading = false;
            item.searchError = '';
            renderOrderItemSearchUI(itemKey);
        }

        function clearOrderItemProduct(itemKey, clearFields = false) {
            const item = getOrderItemDraft(itemKey);
            if (!item) {
                return;
            }

            clearSearchDebounce(item);
            item.searchQuery = '';
            item.searchResults = [];
            item.selectedProduct = null;
            item.searchLoading = false;
            item.searchError = '';
            item.searchRequestSeq += 1;
            item.product_id = '';

            if (clearFields) {
                item.product_article = '';
                item.product_name = '';
            }

            renderOrderItemSearchUI(itemKey);
        }

        function addOrderDraftItem() {
            ensureOrderDraftDefaults();
            const item = createOrderItemDraft();
            item.item_currency_id = String(getDefaultCurrencyID() || '');
            state.orderDraft.items.push(item);
            renderOrderCreate();
        }

        function removeOrderDraftItem(itemKey) {
            if (state.orderDraft.items.length <= 1) {
                return;
            }

            const item = getOrderItemDraft(itemKey);
            if (item) {
                clearSearchDebounce(item);
            }

            state.orderDraft.items = state.orderDraft.items.filter((entry) => entry.key !== itemKey);
            renderOrderCreate();
        }

        function renderRecentOrderRow(item) {
            return `
                <div class="row">
                    <div class="row-title">Заказ #${escapeHtml(item.order_id)}</div>
                    <div class="row-subtitle">${escapeHtml(item.order_customer || 'Клиент не указан')}</div>
                    <div class="row-subtitle">${escapeHtml(item.order_establishment_name || '-')}
                        <span class="status-inline">• ${escapeHtml(item.order_status || 'Без статуса')}</span>
                    </div>
                </div>
            `;
        }

        function renderRecentInventoryRow(item) {
            return `
                <div class="row">
                    <div class="row-title">Инвентаризация #${escapeHtml(item.inventory_id)}</div>
                    <div class="row-subtitle">${escapeHtml(item.inventory_establishment_name || '-')}</div>
                    <div class="row-subtitle">${escapeHtml(item.inventory_supplier || 'Без поставщика')} • ${escapeHtml(item.inventory_status || 'Без статуса')}</div>
                </div>
            `;
        }

        function renderRecentProductRegistrationRow(item) {
            return `
                <div class="row">
                    <div class="row-title">Приемка #${escapeHtml(item.product_registration_id)}</div>
                    <div class="row-subtitle">${escapeHtml(item.product_registration_supplier || '-')}</div>
                    <div class="row-subtitle">${escapeHtml(item.product_registration_establishment_name || '-')} • ${escapeHtml(item.product_registration_status || 'Без статуса')}</div>
                </div>
            `;
        }

        function renderOrderDraftItem(item, index, orderItemStatuses) {
            const query = String(item.searchQuery || '').trim();
            const selected = item.selectedProduct;
            let metaText = 'Введи минимум 2 символа: поиск идёт по артикулу и названию товара.';

            if (item.searchError) {
                metaText = item.searchError;
            } else if (item.searchLoading) {
                metaText = 'Ищем товары в каталоге...';
            } else if (selected) {
                metaText = 'Товар выбран. Поля артикула и названия синхронизированы с каталогом.';
            } else if (query.length >= 2 && !item.searchResults.length) {
                metaText = 'Ничего не найдено. Можно ввести артикул и название вручную.';
            } else if (query.length >= 2) {
                metaText = `Найдено: ${item.searchResults.length}`;
            }

            const summary = selected ? `
                <div class="product-search-summary">
                    <div>
                        <strong>${escapeHtml(formatProductSearchLabel(selected))}</strong>
                        <span>${selected.product_cost_usd != null ? `Каталог: ${escapeHtml(selected.product_cost_usd)} USD` : 'Цена в каталоге не заполнена'}</span>
                    </div>
                    <button class="ghost-button" type="button" data-order-item-clear-product="${escapeHtml(item.key)}">Сбросить</button>
                </div>
            ` : '';

            const results = !selected && query.length >= 2 ? item.searchResults.map((product) => `
                <button class="product-search-item" type="button" data-order-item-select-product="${escapeHtml(item.key)}" data-product-id="${escapeHtml(product.product_id)}">
                    <span class="product-search-primary">${escapeHtml(product.product_name || 'Без названия')}</span>
                    <span class="product-search-secondary">Артикул: ${escapeHtml(product.product_article || '-')} • ID: ${escapeHtml(product.product_id || '-')}</span>
                </button>
            `).join('') : '';

            return `
                <div class="row stack" data-order-item-row="${escapeHtml(item.key)}">
                    <div class="row-top">
                        <div>
                            <div class="row-title">Позиция ${index + 1}</div>
                            <div class="row-subtitle">Каждую позицию можно найти по каталогу или заполнить вручную.</div>
                        </div>
                        <div class="row-actions">
                            ${state.orderDraft.items.length > 1 ? `<button class="ghost-button" type="button" data-order-remove-item="${escapeHtml(item.key)}">Удалить позицию</button>` : ''}
                        </div>
                    </div>
                    <input type="hidden" data-order-item-field="product_id" data-item-key="${escapeHtml(item.key)}" value="${escapeHtml(item.product_id)}">
                    <div class="field field-wide">
                        <label>Поиск товара</label>
                        <div class="product-search">
                            <div class="product-search-head">
                                <input data-order-item-search-input="${escapeHtml(item.key)}" value="${escapeHtml(selected ? formatProductSearchLabel(selected) : item.searchQuery)}" placeholder="Начни вводить артикул или название товара">
                            </div>
                            <div class="product-search-meta${item.searchError ? ' error' : ''}" data-order-item-meta="${escapeHtml(item.key)}">${escapeHtml(metaText)}</div>
                            <div data-order-item-summary="${escapeHtml(item.key)}">${summary}</div>
                            <div class="product-search-results" data-order-item-results="${escapeHtml(item.key)}">${results}</div>
                        </div>
                    </div>
                    <div class="form-grid">
                        <div class="field"><label>Артикул</label><input data-order-item-field="product_article" data-item-key="${escapeHtml(item.key)}" value="${escapeHtml(item.product_article)}" placeholder="NEW-001" required></div>
                        <div class="field"><label>Название товара</label><input data-order-item-field="product_name" data-item-key="${escapeHtml(item.key)}" value="${escapeHtml(item.product_name)}" placeholder="Название из каталога или вручную" required></div>
                        <div class="field"><label>Количество</label><input data-order-item-field="item_quantity" data-item-key="${escapeHtml(item.key)}" type="number" min="1" value="${escapeHtml(item.item_quantity)}" required></div>
                        <div class="field"><label>Цена</label><input data-order-item-field="item_price" data-item-key="${escapeHtml(item.key)}" type="number" step="0.01" min="0" value="${escapeHtml(item.item_price)}" required></div>
                        <div class="field"><label>Валюта</label><select data-order-item-field="item_currency_id" data-item-key="${escapeHtml(item.key)}">${renderSelectOptions(state.currencies, (currency) => currency.currency_id, (currency) => `${currency.currency_name}${currency.currency_sign ? ` (${currency.currency_sign})` : ''}`, item.item_currency_id)}</select></div>
                        <div class="field"><label>Статус позиции</label><select data-order-item-field="order_item_status_id" data-item-key="${escapeHtml(item.key)}"><option value="">По умолчанию</option>${renderSelectOptions(orderItemStatuses, (status) => status.status_id, (status) => status.status_status, item.order_item_status_id)}</select></div>
                    </div>
                </div>
            `;
        }

        function renderOrderCreate() {
            ensureOrderDraftDefaults();
            const orderStatuses = getStatusesByType('orders');
            const orderItemStatuses = getStatusesByType('order_products');

            cards.orderCreate.innerHTML = `
                <div class="card-header">
                    <div>
                        <h3>Создание заказа</h3>
                        <p>Заказ теперь собирается как рабочий лист: точка, метод и статус выбираются кнопками, а товары можно добавить вручную или подтянуть через импорт.</p>
                    </div>
                    <div class="pill">${state.orders.length} orders</div>
                </div>
                <div class="section-banner">
                    <p>Быстрый сценарий: сначала подтяни строки через импорт на вкладке Импорт, потом здесь проверь клиента, адрес и состав заказа.</p>
                </div>
                <form class="inline-form" data-document-form="order">
                    <div class="form-grid">
                        <div class="field">
                            <label>Точка</label>
                            <div class="choice-grid">${renderChoiceButtons(state.establishments, (item) => item.establishment_id, (item) => item.establishment_name, state.orderDraft.order_establishment_id, { field: 'order_establishment_id' })}</div>
                        </div>
                        <div class="field">
                            <label>Метод</label>
                            <div class="choice-grid">${renderChoiceButtons(state.orderMethods, (item) => item.order_method_id, (item) => item.order_method_name, state.orderDraft.order_method_id, { field: 'order_method_id' })}</div>
                        </div>
                        <div class="field">
                            <label>Подметод</label>
                            <input name="order_sub_method" data-order-meta-field="order_sub_method" value="${escapeHtml(state.orderDraft.order_sub_method)}" placeholder="Авито / СДЭК / Яндекс">
                        </div>
                        <div class="field">
                            <label>Способ связи</label>
                            <div class="choice-grid">${renderChoiceButtons(ORDER_CONTACT_METHODS, (item) => item, (item) => item, state.orderDraft.order_contact_method, { field: 'order_contact_method', allowEmpty: true, emptyLabel: 'Не указан' })}</div>
                        </div>
                        <div class="field">
                            <label>Статус заказа</label>
                            <div class="choice-grid">${renderChoiceButtons(orderStatuses, (item) => item.status_id, (item) => item.status_status, state.orderDraft.order_status_id, { field: 'order_status_id', allowEmpty: true, emptyLabel: 'По умолчанию' })}</div>
                        </div>
                        <div class="field">
                            <label>Клиент</label>
                            <input name="order_customer" data-order-meta-field="order_customer" value="${escapeHtml(state.orderDraft.order_customer)}" placeholder="Марина" required>
                        </div>
                        <div class="field">
                            <label>Комментарий к чату</label>
                            <input name="message_text" data-order-meta-field="message_text" value="${escapeHtml(state.orderDraft.message_text)}" placeholder="Новый заказ из NufNaf Admin">
                        </div>
                        <div class="field field-wide">
                            <label>Информация / адрес</label>
                            <input name="order_info" data-order-meta-field="order_info" value="${escapeHtml(state.orderDraft.order_info)}" placeholder="г. Москва, улица Восьмая 6" required>
                        </div>
                    </div>
                    <div class="stack">
                        ${state.orderDraft.items.map((item, index) => renderOrderDraftItem(item, index, orderItemStatuses)).join('')}
                    </div>
                    <div class="row-actions">
                        <button class="ghost-button" type="button" data-order-add-item="true">Добавить ещё товар</button>
                        <button class="button" type="submit">Создать заказ</button>
                    </div>
                </form>
                <div class="stack">
                    <div class="row-subtitle">Последние заказы</div>
                    <div class="compact-list">${state.orders.length ? state.orders.map((item) => renderRecentOrderRow(item)).join('') : '<div class="empty">Пока нет заказов</div>'}</div>
                </div>
            `;
        }

        function renderInventoryCreate() {
            const inventoryStatuses = getStatusesByType('inventory');
            const defaultCurrencyID = getDefaultCurrencyID();

            cards.inventoryCreate.innerHTML = `
                <div class="card-header">
                    <div>
                        <h3>Инвентаризация</h3>
                        <p>Отдельный поток только для инвентаризации. Здесь не смешиваются приемки и заказы.</p>
                    </div>
                    <div class="pill">${state.inventories.length} inventories</div>
                </div>
                <form class="inline-form" data-document-form="inventory">
                    <div class="form-grid single">
                        <input name="product_id" type="hidden" value="">
                        <div class="field"><label>Точка</label><select name="inventory_establishment_id" required>${renderSelectOptions(state.establishments, (item) => item.establishment_id, (item) => item.establishment_name)}</select></div>
                        <div class="field"><label>Поставщик</label><input name="inventory_supplier" placeholder="ООО Восток"></div>
                        <div class="field"><label>Комментарий к чату</label><input name="message_text" placeholder="Инвентаризация с web admin"></div>
                        <div class="field"><label>Статус</label><select name="inventory_status_id"><option value="">По умолчанию</option>${renderSelectOptions(inventoryStatuses, (item) => item.status_id, (item) => item.status_status)}</select></div>
                        <div class="field field-wide">
                            <label>Поиск товара</label>
                            <div class="product-search" data-single-product-search="inventory">
                                <div class="product-search-head">
                                    <input name="product_search" data-single-product-search-input="inventory" placeholder="Найди товар по артикулу или названию">
                                </div>
                                <div class="product-search-meta" data-single-product-meta="inventory">Введи минимум 2 символа: можно искать по артикулу и по названию.</div>
                                <div data-single-product-summary="inventory"></div>
                                <div class="product-search-results" data-single-product-results="inventory"></div>
                            </div>
                        </div>
                        <div class="field"><label>Артикул</label><input name="product_article" placeholder="INV-001" required></div>
                        <div class="field"><label>Название товара</label><input name="product_name" placeholder="Inventory Item" required></div>
                        <div class="field"><label>Количество</label><input name="item_quantity" type="number" min="1" value="1" required></div>
                        <div class="field"><label>Себестоимость</label><input name="item_cost" type="number" step="0.01" min="0" value="0.00" required></div>
                        <div class="field"><label>Валюта</label><select name="item_currency_id">${renderSelectOptions(state.currencies, (item) => item.currency_id, (item) => `${item.currency_name}${item.currency_sign ? ` (${item.currency_sign})` : ''}`, defaultCurrencyID)}</select></div>
                    </div>
                    <button class="button" type="submit">Создать инвентаризацию</button>
                </form>
                <div class="compact-list">${state.inventories.length ? state.inventories.map((item) => renderRecentInventoryRow(item)).join('') : '<div class="empty">Пока нет инвентаризаций</div>'}</div>
            `;

            renderSingleDocumentProductSearchUI('inventory');
        }

        function renderProductRegistrationCreate() {
            const registrationStatuses = getStatusesByType('product_registration');
            const defaultCurrencyID = getDefaultCurrencyID();

            cards.productRegistrationCreate.innerHTML = `
                <div class="card-header">
                    <div>
                        <h3>Приемка товара</h3>
                        <p>Отдельный поток для приемок поставки, без смешивания с заказами и инвентаризацией.</p>
                    </div>
                    <div class="pill">${state.productRegistrations.length} receipts</div>
                </div>
                <form class="inline-form" data-document-form="productRegistration">
                    <div class="form-grid single">
                        <input name="product_id" type="hidden" value="">
                        <div class="field"><label>Точка</label><select name="product_registration_establishment_id" required>${renderSelectOptions(state.establishments, (item) => item.establishment_id, (item) => item.establishment_name)}</select></div>
                        <div class="field"><label>Поставщик</label><input name="product_registration_supplier" placeholder="ЗАО Север" required></div>
                        <div class="field"><label>Комментарий к чату</label><input name="message_text" placeholder="Новая приемка с web admin"></div>
                        <div class="field"><label>Статус</label><select name="product_registration_status_id"><option value="">По умолчанию</option>${renderSelectOptions(registrationStatuses, (item) => item.status_id, (item) => item.status_status)}</select></div>
                        <div class="field field-wide">
                            <label>Поиск товара</label>
                            <div class="product-search" data-single-product-search="productRegistration">
                                <div class="product-search-head">
                                    <input name="product_search" data-single-product-search-input="productRegistration" placeholder="Найди товар по артикулу или названию">
                                </div>
                                <div class="product-search-meta" data-single-product-meta="productRegistration">Введи минимум 2 символа: можно искать по артикулу и по названию.</div>
                                <div data-single-product-summary="productRegistration"></div>
                                <div class="product-search-results" data-single-product-results="productRegistration"></div>
                            </div>
                        </div>
                        <div class="field"><label>Артикул</label><input name="product_article" placeholder="PR-001" required></div>
                        <div class="field"><label>Название товара</label><input name="product_name" placeholder="Receipt Item" required></div>
                        <div class="field"><label>Количество</label><input name="item_quantity" type="number" min="1" value="1" required></div>
                        <div class="field"><label>Себестоимость</label><input name="item_cost" type="number" step="0.01" min="0" value="0.00" required></div>
                        <div class="field"><label>Валюта</label><select name="item_currency_id">${renderSelectOptions(state.currencies, (item) => item.currency_id, (item) => `${item.currency_name}${item.currency_sign ? ` (${item.currency_sign})` : ''}`, defaultCurrencyID)}</select></div>
                    </div>
                    <button class="button" type="submit">Создать приемку</button>
                </form>
                <div class="compact-list">${state.productRegistrations.length ? state.productRegistrations.map((item) => renderRecentProductRegistrationRow(item)).join('') : '<div class="empty">Пока нет приемок</div>'}</div>
            `;

            renderSingleDocumentProductSearchUI('productRegistration');
        }

        function renderProductImport() {
            const statusClass = state.productImportStatusType ? ` row-subtitle ${state.productImportStatusType}` : 'row-subtitle';
            const summary = state.lastProductImport
                ? `<div class="row-subtitle">Последний импорт: создано ${escapeHtml(state.lastProductImport.created)}, обновлено ${escapeHtml(state.lastProductImport.updated)}, пропущено ${escapeHtml(state.lastProductImport.skipped)}, обработано ${escapeHtml(state.lastProductImport.processed || 0)} из ${escapeHtml(state.lastProductImport.total_rows || 0)}.</div>`
                : '<div class="row-subtitle">Поддерживается импорт из Excel по колонкам: A = артикул, B = название, D = цена USD. Строки без значения в колонке A пропускаются.</div>';
            const status = state.productImportStatus
                ? `<div class="${statusClass.trim()}">${escapeHtml(state.productImportStatus)}</div>`
                : '';
            const orderImportStatusClass = state.orderImport.statusType ? ` row-subtitle ${state.orderImport.statusType}` : 'row-subtitle';
            const orderImportStatus = state.orderImport.status
                ? `<div class="${orderImportStatusClass.trim()}">${escapeHtml(state.orderImport.status)}</div>`
                : '';
            const importPreview = state.orderImport.parsedRows.length ? `
                <div class="import-preview">
                    ${state.orderImport.parsedRows.map((row) => `
                        <div class="import-preview-row ${row.matchedProduct ? 'matched' : 'missing'}">
                            <strong>${escapeHtml(row.nomenclature)}</strong>
                            <div class="import-preview-meta">Количество: ${escapeHtml(row.quantity)} • Цена: ${escapeHtml(row.price)}</div>
                            <div class="import-preview-meta">${row.matchedProduct ? `Совпадение: ${escapeHtml(formatProductSearchLabel(row.matchedProduct))}` : 'Совпадение в каталоге не найдено, строка попадет как ручная позиция.'}</div>
                        </div>
                    `).join('')}
                </div>
            ` : '<div class="empty">Пока нет импортированных строк заказа</div>';

            cards.productImport.innerHTML = `
                <div class="card-header">
                    <div>
                        <h3>Импорт</h3>
                        <p>Одна зона для каталога, вторая для быстрой сборки заказа из таблицы товаров с ценой.</p>
                    </div>
                    <div class="pill">${state.productsTotal} products</div>
                </div>
                <div class="split-panels">
                    <form class="inline-form import-panel" data-product-import-form="true">
                        <div>
                            <h4>Импорт каталога из XLSX</h4>
                            <p>Загрузи прайс в формате Excel. Будут обработаны только строки, где заполнена колонка A.</p>
                        </div>
                        <div class="form-grid single">
                            <div class="field">
                                <label>Файл Excel (.xlsx)</label>
                                <input name="file" type="file" accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" required ${state.isProductImportRunning ? 'disabled' : ''}>
                            </div>
                        </div>
                        <div class="row-actions">
                            <button class="button" type="submit" ${state.isProductImportRunning ? 'disabled' : ''}>${state.isProductImportRunning ? 'Идёт импорт...' : 'Импортировать товары'}</button>
                        </div>
                        ${status}
                        ${summary}
                    </form>
                    <form class="inline-form import-panel" data-order-import-form="true">
                        <div>
                            <h4>Импорт строк заказа</h4>
                            <p>Вставь таблицу строками: номенклатура, количество, цена. Поддерживаются табы, `;` и запятые. Найденные совпадения попадут в новый заказ.</p>
                        </div>
                        <div class="form-grid single">
                            <div class="field">
                                <label>Таблица товаров</label>
                                <textarea name="order_import_text" data-order-import-raw="true" placeholder="Куртка синяя	2	3990\nАртикул-123	1	1490">${escapeHtml(state.orderImport.rawText)}</textarea>
                            </div>
                        </div>
                        <div class="row-actions">
                            <button class="button" type="submit" ${state.orderImport.loading ? 'disabled' : ''}>${state.orderImport.loading ? 'Ищем совпадения...' : 'Добавить в заказ'}</button>
                        </div>
                        ${orderImportStatus}
                        ${importPreview}
                    </form>
                </div>
            `;
        }

        function wait(delayMs) {
            return new Promise((resolve) => window.setTimeout(resolve, delayMs));
        }

        async function waitForProductImportCompletion(jobID) {
            for (;;) {
                const payload = await request(`/products/import-xlsx/${jobID}`, { method: 'GET' });
                const item = payload.item;
                state.lastProductImport = item;

                if (item.status === 'completed') {
                    state.isProductImportRunning = false;
                    state.currentProductImportJobId = '';
                    state.productImportStatus = `Импорт завершён: обработано ${item.processed || 0} из ${item.total_rows || 0}, создано ${item.created}, обновлено ${item.updated}, пропущено ${item.skipped}.`;
                    state.productImportStatusType = 'ok';
                    return item;
                }

                if (item.status === 'failed') {
                    state.isProductImportRunning = false;
                    state.currentProductImportJobId = '';
                    state.productImportStatus = item.error_message || 'Импорт завершился с ошибкой';
                    state.productImportStatusType = 'error';
                    throw new Error(state.productImportStatus);
                }

                state.productImportStatus = `Идёт импорт: обработано ${item.processed || 0} из ${item.total_rows || 0}, создано ${item.created}, обновлено ${item.updated}, пропущено ${item.skipped}.`;
                state.productImportStatusType = '';
                renderProductImport();
                await wait(800);
            }
        }

        function renderMessageSender() {
            const currentUserID = state.user?.user_id;
            cards.messageSender.innerHTML = `
                <div class="card-header">
                    <div>
                        <h3>Мини-чат для проверки push</h3>
                        <p>Видно последние сообщения, от кого они пришли и что только что отправилось из web admin. Это удобно для проверки, что на iPhone открыт другой профиль.</p>
                    </div>
                    <div class="pill">${state.messages.length} messages</div>
                </div>
                <div class="chat-shell">
                    <div class="chat-toolbar">
                        <div class="chat-hint">
                            Web admin сейчас вошел как <strong>${escapeHtml(state.user?.user_login || '-')}</strong>.
                            На iPhone должен быть открыт другой пользователь, если ты проверяешь доставку push между разными аккаунтами.
                        </div>
                        <button class="ghost-button" type="button" data-refresh-chat="true">Обновить чат</button>
                    </div>
                    <div class="chat-feed">
                        ${state.messages.length ? state.messages.map((item) => renderChatMessageRow(item, currentUserID)).join('') : '<div class="chat-empty">Сообщений пока нет. Отправь первое сообщение из web admin и проверь, отобразилось ли оно здесь и на телефоне.</div>'}
                    </div>
                    <form class="inline-form chat-composer" data-send-message-form="true">
                        <div class="field">
                            <label>Текст сообщения</label>
                            <textarea name="message_text" placeholder="Например: тест push из web admin" required></textarea>
                        </div>
                        <div class="row-actions">
                            <button class="button" type="submit">Отправить сообщение</button>
                        </div>
                    </form>
                </div>
            `;

            scrollChatFeedToBottom();
        }

        function scrollChatFeedToBottom() {
            requestAnimationFrame(() => {
                const feed = cards.messageSender.querySelector('.chat-feed');
                if (!feed) {
                    return;
                }
                feed.scrollTop = feed.scrollHeight;
            });
        }

        function renderChatMessageRow(item, currentUserID) {
            const isOwn = item.message_owner_user_id === currentUserID;
            const authorName = formatMessageAuthor(item);
            const authorMeta = item.message_owner_user_login ? `@${escapeHtml(item.message_owner_user_login)}` : '';
            const timestamp = formatChatTimestamp(item.message_created_at);
            const body = describeMessageBody(item);

            return `
                <div class="chat-row${isOwn ? ' own' : ''}">
                    <div class="chat-bubble">
                        <div class="chat-meta">
                            <span class="chat-author">${escapeHtml(authorName)}${authorMeta ? ` <span>${authorMeta}</span>` : ''}</span>
                            <span>${escapeHtml(timestamp)}</span>
                        </div>
                        <div class="chat-type">${escapeHtml(formatMessageType(item))}</div>
                        <div class="chat-text">${escapeHtml(body)}</div>
                    </div>
                </div>
            `;
        }

        function formatMessageAuthor(item) {
            const fullName = `${item.message_owner_second_name || ''} ${item.message_owner_first_name || ''}`.trim();
            return fullName || item.message_owner_user_login || `user ${item.message_owner_user_id || '?'}`;
        }

        function formatChatTimestamp(value) {
            if (!value) {
                return 'время неизвестно';
            }
            const date = new Date(value);
            if (Number.isNaN(date.getTime())) {
                return value;
            }
            return date.toLocaleString('ru-RU', {
                day: '2-digit',
                month: '2-digit',
                hour: '2-digit',
                minute: '2-digit',
            });
        }

        function formatMessageType(item) {
            switch (item.message_type) {
                case 'message':
                    return 'Сообщение';
                case 'file':
                    return 'Файл';
                case 'order':
                    return 'Заказ';
                case 'inventory':
                    return 'Инвентаризация';
                case 'product_registration':
                    return 'Приемка';
                default:
                    return item.message_type || 'Сообщение';
            }
        }

        function describeMessageBody(item) {
            if (item.message_text && item.message_text.trim()) {
                return item.message_text;
            }
            if (item.order) {
                return `Заказ #${item.order.order_id || item.message_order_id || ''}${item.message_status ? ` • ${item.message_status}` : ''}`;
            }
            if (item.inventory) {
                return `Инвентаризация #${item.inventory.inventory_id || item.message_inventory_id || ''}${item.message_status ? ` • ${item.message_status}` : ''}`;
            }
            if (item.product_registration) {
                return `Приемка #${item.product_registration.product_registration_id || item.message_product_registration_id || ''}${item.message_status ? ` • ${item.message_status}` : ''}`;
            }
            if (Array.isArray(item.attachments) && item.attachments.length) {
                return item.attachments.map((attachment) => attachment.attachment_original_filename || attachment.attachment_kind || 'вложение').join(', ');
            }
            return 'Пустое сообщение';
        }

        function renderPendingUsers() {
            cards.pendingUsers.innerHTML = `
                <div class="card-header">
                    <div>
                        <h3>Пользователи на активацию</h3>
                        <p>Новые регистрации попадают сюда до подтверждения администратором.</p>
                    </div>
                    <div class="pill">${state.pendingUsers.length} pending</div>
                </div>
                <div class="list">
                    ${state.pendingUsers.length ? state.pendingUsers.map((item) => renderPendingUserRow(item)).join('') : '<div class="empty">Нет заявок на активацию</div>'}
                </div>
            `;
        }

        function renderPendingUserRow(item) {
            const fullName = `${item.user_second_name || ''} ${item.user_first_name || ''}`.trim() || 'Имя не указано';
            const createdAt = item.user_created_at ? new Date(item.user_created_at).toLocaleString('ru-RU') : 'Дата не указана';

            return `
                <div class="row">
                    <div class="row-top">
                        <div>
                            <div class="row-title">${escapeHtml(item.user_login)}</div>
                            <div class="row-subtitle">${escapeHtml(fullName)}</div>
                            <div class="row-subtitle">Создан: ${escapeHtml(createdAt)}</div>
                            <div class="row-subtitle">Возраст: ${escapeHtml(item.user_age ?? 0)} | Адрес: ${escapeHtml(item.user_address || '-')}</div>
                        </div>
                        <div class="row-actions">
                            <button class="button" type="button" data-activate-user="${item.user_id}">Активировать</button>
                        </div>
                    </div>
                </div>
            `;
        }

        function renderUsers() {
            cards.users.innerHTML = `
                <div class="card-header">
                    <div>
                        <h3>Все пользователи</h3>
                        <p>Общий список пользователей с текущими ролями и статусами активации.</p>
                    </div>
                    <div class="pill">${state.users.length} users</div>
                </div>
                <div class="list">
                    ${state.users.length ? state.users.map((item) => renderUserRow(item)).join('') : '<div class="empty">Пользователи не найдены</div>'}
                </div>
            `;
        }

        function renderUserRow(item) {
            const fullName = `${item.user_second_name || ''} ${item.user_first_name || ''}`.trim() || 'Имя не указано';
            const createdAt = item.user_created_at ? new Date(item.user_created_at).toLocaleString('ru-RU') : 'Дата не указана';
            const badges = [
                item.user_admin ? 'admin' : 'user',
                item.user_active ? 'active' : 'pending',
            ];

            return `
                <div class="row">
                    <div class="row-top">
                        <div>
                            <div class="row-title">${escapeHtml(item.user_login)}</div>
                            <div class="row-subtitle">${escapeHtml(fullName)}</div>
                            <div class="row-subtitle">Создан: ${escapeHtml(createdAt)}</div>
                        </div>
                        <div class="row-actions">
                            ${badges.map((badge) => `<span class="pill">${escapeHtml(badge)}</span>`).join('')}
                        </div>
                    </div>
                </div>
            `;
        }

        async function activateUser(userID) {
            await request(`/users/${userID}`, {
                method: 'PUT',
                body: JSON.stringify({ user_active: true }),
            });
        }

        function renderEstablishments() {
            cards.establishments.innerHTML = `
                <div class="card-header">
                    <div>
                        <h3>Точки</h3>
                        <p>Редактирование establishments для документов и заказов.</p>
                    </div>
                </div>
                <form class="inline-form" data-create-form="establishments">
                    <div class="form-grid single">
                        <div class="field"><label>Название</label><input name="establishment_name" required></div>
                        <div class="field"><label>Адрес</label><input name="establishment_address"></div>
                    </div>
                    <button class="button" type="submit">Добавить точку</button>
                </form>
                <div class="list">
                    ${state.establishments.length ? state.establishments.map((item) => renderEstablishmentRow(item)).join('') : '<div class="empty">Список пуст</div>'}
                </div>
            `;
        }

        function renderEstablishmentRow(item) {
            const key = `establishments:${item.establishment_id}`;
            const editing = state.editing[key];
            if (editing) {
                return `
                    <form class="row inline-form" data-edit-form="establishments" data-id="${item.establishment_id}">
                        <div class="form-grid single">
                            <div class="field"><label>Название</label><input name="establishment_name" value="${escapeHtml(editing.establishment_name)}" required></div>
                            <div class="field"><label>Адрес</label><input name="establishment_address" value="${escapeHtml(editing.establishment_address || '')}"></div>
                        </div>
                        <div class="row-actions">
                            <button class="button" type="submit">Сохранить</button>
                            <button class="ghost-button" type="button" data-cancel-edit="establishments" data-id="${item.establishment_id}">Отмена</button>
                        </div>
                    </form>
                `;
            }

            return `
                <div class="row">
                    <div class="row-top">
                        <div>
                            <div class="row-title">${escapeHtml(item.establishment_name)}</div>
                            <div class="row-subtitle">${escapeHtml(item.establishment_address || 'Адрес не указан')}</div>
                        </div>
                        <div class="row-actions">
                            <button class="ghost-button" type="button" data-edit="establishments" data-id="${item.establishment_id}">Изменить</button>
                        </div>
                    </div>
                </div>
            `;
        }

        function renderOrderMethods() {
            cards.orderMethods.innerHTML = `
                <div class="card-header">
                    <div>
                        <h3>Методы заказа</h3>
                        <p>Курьер, самовывоз, СДЭК и другие способы доставки.</p>
                    </div>
                </div>
                <form class="inline-form" data-create-form="orderMethods">
                    <div class="form-grid single">
                        <div class="field"><label>Название метода</label><input name="order_method_name" required></div>
                    </div>
                    <button class="button" type="submit">Добавить метод</button>
                </form>
                <div class="list">
                    ${state.orderMethods.length ? state.orderMethods.map((item) => renderOrderMethodRow(item)).join('') : '<div class="empty">Список пуст</div>'}
                </div>
            `;
        }

        function renderOrderMethodRow(item) {
            const key = `orderMethods:${item.order_method_id}`;
            const editing = state.editing[key];
            if (editing) {
                return `
                    <form class="row inline-form" data-edit-form="orderMethods" data-id="${item.order_method_id}">
                        <div class="form-grid single">
                            <div class="field"><label>Название метода</label><input name="order_method_name" value="${escapeHtml(editing.order_method_name)}" required></div>
                        </div>
                        <div class="row-actions">
                            <button class="button" type="submit">Сохранить</button>
                            <button class="ghost-button" type="button" data-cancel-edit="orderMethods" data-id="${item.order_method_id}">Отмена</button>
                        </div>
                    </form>
                `;
            }

            return `
                <div class="row">
                    <div class="row-top">
                        <div>
                            <div class="row-title">${escapeHtml(item.order_method_name)}</div>
                        </div>
                        <div class="row-actions">
                            <button class="ghost-button" type="button" data-edit="orderMethods" data-id="${item.order_method_id}">Изменить</button>
                        </div>
                    </div>
                </div>
            `;
        }

        function renderStatuses() {
            const groupedStatuses = state.statuses.reduce((accumulator, item) => {
                const key = item.status_type || 'unknown';
                if (!accumulator[key]) {
                    accumulator[key] = [];
                }
                accumulator[key].push(item);
                return accumulator;
            }, {});

            cards.statuses.innerHTML = `
                <div class="card-header">
                    <div>
                        <h3>Статусы</h3>
                        <p>Статусы только читаются из базы. Добавление из админки отключено, чтобы клиент не ловил неконсистентные записи.</p>
                    </div>
                </div>
                <div class="status-groups">
                    ${Object.keys(groupedStatuses).length ? Object.entries(groupedStatuses).map(([type, items]) => `
                        <div class="status-group">
                            <div>
                                <h4>${escapeHtml(type)}</h4>
                                <p>${escapeHtml(items.length)} статусов доступны из БД</p>
                            </div>
                            <div class="status-chip-list">
                                ${items.map((item) => `<span class="status-chip">${escapeHtml(item.status_status)}${item.status_color ? ` • ${escapeHtml(item.status_color)}` : ''}</span>`).join('')}
                            </div>
                        </div>
                    `).join('') : '<div class="empty">Список пуст</div>'}
                </div>
            `;
        }

        function renderCurrencies() {
            cards.currencies.innerHTML = `
                <div class="card-header">
                    <div>
                        <h3>Валюты</h3>
                        <p>Справочник валют, используемый в документах и позициях.</p>
                    </div>
                </div>
                <form class="inline-form" data-create-form="currencies">
                    <div class="form-grid">
                        <div class="field"><label>Название</label><input name="currency_name" placeholder="USD" required></div>
                        <div class="field"><label>Знак</label><input name="currency_sign" placeholder="$"></div>
                    </div>
                    <button class="button" type="submit">Добавить валюту</button>
                </form>
                <div class="list">
                    ${state.currencies.length ? state.currencies.map((item) => renderCurrencyRow(item)).join('') : '<div class="empty">Список пуст</div>'}
                </div>
            `;
        }

        function renderCurrencyRow(item) {
            const key = `currencies:${item.currency_id}`;
            const editing = state.editing[key];
            if (editing) {
                return `
                    <form class="row inline-form" data-edit-form="currencies" data-id="${item.currency_id}">
                        <div class="form-grid">
                            <div class="field"><label>Название</label><input name="currency_name" value="${escapeHtml(editing.currency_name)}" required></div>
                            <div class="field"><label>Знак</label><input name="currency_sign" value="${escapeHtml(editing.currency_sign || '')}"></div>
                        </div>
                        <div class="row-actions">
                            <button class="button" type="submit">Сохранить</button>
                            <button class="ghost-button" type="button" data-cancel-edit="currencies" data-id="${item.currency_id}">Отмена</button>
                        </div>
                    </form>
                `;
            }

            return `
                <div class="row">
                    <div class="row-top">
                        <div>
                            <div class="row-title">${escapeHtml(item.currency_name)}</div>
                            <div class="row-subtitle">${escapeHtml(item.currency_sign || 'без знака')}</div>
                        </div>
                        <div class="row-actions">
                            <button class="ghost-button" type="button" data-edit="currencies" data-id="${item.currency_id}">Изменить</button>
                        </div>
                    </div>
                </div>
            `;
        }

        function buildPayload(section, formData) {
            switch (section) {
                case 'establishments':
                    return {
                        establishment_name: formData.get('establishment_name'),
                        establishment_address: formData.get('establishment_address') || null,
                    };
                case 'orderMethods':
                    return {
                        order_method_name: formData.get('order_method_name'),
                    };
                case 'statuses':
                    return {
                        status_type: formData.get('status_type'),
                        status_status: formData.get('status_status'),
                        status_color: formData.get('status_color') || null,
                    };
                case 'currencies':
                    return {
                        currency_name: formData.get('currency_name'),
                        currency_sign: formData.get('currency_sign') || null,
                    };
                default:
                    return {};
            }
        }

        function buildDocumentPayload(section, formData) {
            const asOptionalString = (key) => {
                const value = String(formData.get(key) || '').trim();
                return value || null;
            };
            const asRequiredString = (key) => String(formData.get(key) || '').trim();
            const asOptionalNumber = (key) => {
                const value = String(formData.get(key) || '').trim();
                return value ? Number(value) : null;
            };
            const asPriceString = (key) => {
                const value = String(formData.get(key) || '').trim();
                return value ? value : '0.00';
            };

            switch (section) {
                case 'order':
                    ensureOrderDraftDefaults();
                    return {
                        order_establishment_id: Number(state.orderDraft.order_establishment_id),
                        order_method_id: Number(state.orderDraft.order_method_id),
                        order_sub_method: state.orderDraft.order_sub_method.trim() || null,
                        order_contact_method: state.orderDraft.order_contact_method.trim() || null,
                        order_customer: state.orderDraft.order_customer.trim(),
                        order_info: state.orderDraft.order_info.trim(),
                        order_status_id: state.orderDraft.order_status_id ? Number(state.orderDraft.order_status_id) : null,
                        message_text: state.orderDraft.message_text.trim() || null,
                        items: state.orderDraft.items.map((item) => ({
                            product_id: item.product_id ? Number(item.product_id) : null,
                            product_article: String(item.product_article || '').trim(),
                            product_name: String(item.product_name || '').trim(),
                            order_item_quantity: Number(item.item_quantity),
                            order_item_price: String(item.item_price || '0.00').trim() || '0.00',
                            order_item_status_id: item.order_item_status_id ? Number(item.order_item_status_id) : null,
                            order_item_currency_id: item.item_currency_id ? Number(item.item_currency_id) : null,
                        })),
                    };
                case 'inventory':
                    return {
                        inventory_establishment_id: Number(formData.get('inventory_establishment_id')),
                        inventory_supplier: asOptionalString('inventory_supplier'),
                        inventory_status_id: asOptionalNumber('inventory_status_id'),
                        message_text: asOptionalString('message_text'),
                        items: [{
                            product_id: asOptionalNumber('product_id'),
                            product_article: asRequiredString('product_article'),
                            product_name: asRequiredString('product_name'),
                            inventory_item_quantity: Number(formData.get('item_quantity')),
                            inventory_item_cost: asPriceString('item_cost'),
                            inventory_item_currency_id: asOptionalNumber('item_currency_id'),
                        }],
                    };
                case 'productRegistration':
                    return {
                        product_registration_establishment_id: Number(formData.get('product_registration_establishment_id')),
                        product_registration_supplier: asRequiredString('product_registration_supplier'),
                        product_registration_status_id: asOptionalNumber('product_registration_status_id'),
                        message_text: asOptionalString('message_text'),
                        items: [{
                            product_id: asOptionalNumber('product_id'),
                            product_article: asRequiredString('product_article'),
                            product_name: asRequiredString('product_name'),
                            product_registration_item_quantity: Number(formData.get('item_quantity')),
                            product_registration_item_cost: asPriceString('item_cost'),
                            product_registration_item_currency_id: asOptionalNumber('item_currency_id'),
                        }],
                    };
                default:
                    throw new Error('Unknown document form');
            }
        }

        function documentConfig(section) {
            switch (section) {
                case 'order':
                    return { path: '/orders', success: 'Заказ создан' };
                case 'inventory':
                    return { path: '/inventories', success: 'Инвентаризация создана' };
                case 'productRegistration':
                    return { path: '/product-registrations', success: 'Приемка создана' };
                default:
                    throw new Error('Unknown document type');
            }
        }

        function sectionConfig(section) {
            switch (section) {
                case 'establishments':
                    return { path: '/establishments' };
                case 'orderMethods':
                    return { path: '/order-methods' };
                case 'statuses':
                    return { path: '/statuses' };
                case 'currencies':
                    return { path: '/currencies' };
                default:
                    throw new Error('Unknown section');
            }
        }

        function updateOrderDraftMeta(field, value) {
            state.orderDraft[field] = value;
        }

        function updateOrderDraftItemField(itemKey, field, value) {
            const item = getOrderItemDraft(itemKey);
            if (!item) {
                return;
            }

            item[field] = value;

            if ((field === 'product_article' || field === 'product_name') && item.selectedProduct) {
                const matchesSelected = item.product_article === (item.selectedProduct.product_article || '')
                    && item.product_name === (item.selectedProduct.product_name || '');

                if (!matchesSelected) {
                    item.selectedProduct = null;
                    item.product_id = '';
                    item.searchQuery = '';
                    item.searchResults = [];
                    renderOrderItemSearchUI(itemKey);
                }
            }
        }

        document.addEventListener('submit', async (event) => {
            if (event.target.dataset.productImportForm) {
                event.preventDefault();
                const formData = new FormData(event.target);
                const file = formData.get('file');

                if (!(file instanceof File) || !file.name) {
                    setMessage(dashboardMessage, 'Выбери xlsx файл для импорта', 'error');
                    return;
                }

                state.isProductImportRunning = true;
                state.productImportStatus = 'Файл отправлен в backend. Запускаем задачу импорта...';
                state.productImportStatusType = '';
                state.lastProductImport = null;
                renderProductImport();
                setMessage(dashboardMessage, 'Импортируем товары из XLSX...');

                try {
                    const uploadData = new FormData();
                    uploadData.append('file', file);
                    const payload = await request('/products/import-xlsx', {
                        method: 'POST',
                        body: uploadData,
                    });
                    state.currentProductImportJobId = payload.item.job_id;
                    event.target.reset();
                    renderProductImport();
                    const completedItem = await waitForProductImportCompletion(payload.item.job_id);
                    await loadDashboardData();
                    state.lastProductImport = completedItem;
                    renderProductImport();
                    setMessage(dashboardMessage, `Импорт завершён: обработано ${completedItem.processed || 0} из ${completedItem.total_rows || 0}, создано ${completedItem.created}, обновлено ${completedItem.updated}, пропущено ${completedItem.skipped}.`, 'ok');
                } catch (error) {
                    state.isProductImportRunning = false;
                    state.currentProductImportJobId = '';
                    state.productImportStatus = error.message;
                    state.productImportStatusType = 'error';
                    renderProductImport();
                    setMessage(dashboardMessage, error.message, 'error');
                }
                return;
            }

            if (event.target.dataset.orderImportForm) {
                event.preventDefault();
                setMessage(dashboardMessage, 'Импортируем строки заказа...');

                try {
                    const formData = new FormData(event.target);
                    await importOrderRowsToDraft(formData.get('order_import_text'));
                    setMessage(dashboardMessage, 'Строки перенесены в создание заказа. Проверь реквизиты и отправляй заказ.', 'ok');
                } catch (error) {
                    state.orderImport.loading = false;
                    state.orderImport.status = error.message;
                    state.orderImport.statusType = 'error';
                    renderProductImport();
                    setMessage(dashboardMessage, error.message, 'error');
                }
                return;
            }

            if (event.target.dataset.sendMessageForm) {
                event.preventDefault();
                setMessage(dashboardMessage, 'Отправляем тестовое сообщение...');

                try {
                    const formData = new FormData(event.target);
                    const payload = await request('/messages', {
                        method: 'POST',
                        body: JSON.stringify({
                            message_type: 'message',
                            message_text: formData.get('message_text'),
                        }),
                    });
                    state.messages = sortMessagesAscending([...(state.messages || []), payload.item]);
                    event.target.reset();
                    renderMessageSender();
                    setMessage(dashboardMessage, 'Сообщение отправлено. Оно уже должно быть видно в мини-чате и на другом профиле.', 'ok');
                } catch (error) {
                    setMessage(dashboardMessage, error.message, 'error');
                }
                return;
            }

            const documentSection = event.target.dataset.documentForm;
            if (documentSection) {
                event.preventDefault();
                setMessage(dashboardMessage, 'Создаём документ...');

                try {
                    const config = documentConfig(documentSection);
                    await request(config.path, {
                        method: 'POST',
                        body: JSON.stringify(buildDocumentPayload(documentSection, new FormData(event.target))),
                    });
                    if (documentSection === 'order') {
                        resetOrderDraft();
                    } else if (documentSection === 'inventory') {
                        resetSingleDocumentProductSearch('inventory');
                    } else if (documentSection === 'productRegistration') {
                        resetSingleDocumentProductSearch('productRegistration');
                    }
                    event.target.reset();
                    await loadDashboardData();
                    setMessage(dashboardMessage, `${config.success}. Документ уже должен появиться в чате и в списке ниже.`, 'ok');
                } catch (error) {
                    setMessage(dashboardMessage, error.message, 'error');
                }
                return;
            }

            const createSection = event.target.dataset.createForm;
            const editSection = event.target.dataset.editForm;
            if (!createSection && !editSection) {
                return;
            }

            event.preventDefault();
            setMessage(dashboardMessage, 'Сохраняем...');

            try {
                if (createSection) {
                    const config = sectionConfig(createSection);
                    await request(config.path, {
                        method: 'POST',
                        body: JSON.stringify(buildPayload(createSection, new FormData(event.target))),
                    });
                    event.target.reset();
                }

                if (editSection) {
                    const config = sectionConfig(editSection);
                    const id = event.target.dataset.id;
                    await request(`${config.path}/${id}`, {
                        method: 'PUT',
                        body: JSON.stringify(buildPayload(editSection, new FormData(event.target))),
                    });
                    delete state.editing[`${editSection}:${id}`];
                }

                await loadDashboardData();
                setMessage(dashboardMessage, 'Данные сохранены', 'ok');
            } catch (error) {
                setMessage(dashboardMessage, error.message, 'error');
            }
        });

        document.addEventListener('click', async (event) => {
            const orderAddItemButton = event.target.closest('[data-order-add-item]');
            const orderRemoveItemButton = event.target.closest('[data-order-remove-item]');
            const orderItemSelectButton = event.target.closest('[data-order-item-select-product]');
            const orderItemClearButton = event.target.closest('[data-order-item-clear-product]');
            const orderChoiceButton = event.target.closest('[data-order-choice-field]');
            const singleProductSelectButton = event.target.closest('[data-single-product-select]');
            const singleProductClearButton = event.target.closest('[data-single-product-clear]');
            const auditRefreshButton = event.target.closest('[data-audit-refresh]');
            const editButton = event.target.closest('[data-edit]');
            const cancelButton = event.target.closest('[data-cancel-edit]');
            const activateButton = event.target.closest('[data-activate-user]');
            const refreshChatButton = event.target.closest('[data-refresh-chat]');
            const menuButton = event.target.closest('[data-dashboard-menu]');
            const managedOrdersPageButton = event.target.closest('[data-managed-orders-page]');
            const managedOrdersReloadButton = event.target.closest('[data-managed-orders-reload]');
            const managedOrderToggleEditButton = event.target.closest('[data-managed-order-toggle-edit]');
            const managedOrderAddItemButton = event.target.closest('[data-managed-order-add-item]');
            const managedOrderRemoveItemButton = event.target.closest('[data-managed-order-remove-item]');
            const managedOrderSaveButton = event.target.closest('[data-managed-order-save]');
            const managedOrderSaveStatusButton = event.target.closest('[data-managed-order-save-status]');
            const contactsTypeButton = event.target.closest('[data-contacts-type]');
            const contactsSearchSubmitButton = event.target.closest('[data-contacts-search-submit]');
            const contactsPageButton = event.target.closest('[data-contacts-page]');

            if (orderAddItemButton) {
                addOrderDraftItem();
                return;
            }

            if (orderRemoveItemButton) {
                removeOrderDraftItem(orderRemoveItemButton.dataset.orderRemoveItem);
                return;
            }

            if (orderItemSelectButton) {
                selectOrderItemProduct(orderItemSelectButton.dataset.orderItemSelectProduct, orderItemSelectButton.dataset.productId);
                return;
            }

            if (orderItemClearButton) {
                clearOrderItemProduct(orderItemClearButton.dataset.orderItemClearProduct, true);
                return;
            }

            if (orderChoiceButton) {
                updateOrderDraftMeta(orderChoiceButton.dataset.orderChoiceField, orderChoiceButton.dataset.orderChoiceValue);
                renderOrderCreate();
                return;
            }

            if (singleProductSelectButton) {
                selectSingleDocumentProduct(singleProductSelectButton.dataset.singleProductSelect, singleProductSelectButton.dataset.productId);
                return;
            }

            if (singleProductClearButton) {
                resetSingleDocumentProductSearch(singleProductClearButton.dataset.singleProductClear, true);
                renderSingleDocumentProductSearchUI(singleProductClearButton.dataset.singleProductClear);
                return;
            }

            if (auditRefreshButton) {
                await loadAuditEvents();
                return;
            }

            if (menuButton) {
                state.activeMenu = menuButton.dataset.dashboardMenu;
                renderDashboardMenu();
                applyDashboardMenuVisibility();
                if (state.activeMenu === 'orders') {
                    await loadOrderManagementPage({ page: state.orderManagement.pagination.page || 1 });
                }
                if (state.activeMenu === 'counterparties') {
                    await loadContactsPage({ page: state.contactsView.pagination.page || 1 });
                }
                return;
            }

            if (managedOrdersPageButton) {
                await loadOrderManagementPage({ page: Number(managedOrdersPageButton.dataset.managedOrdersPage) });
                return;
            }

            if (managedOrdersReloadButton) {
                await loadOrderManagementPage({ page: state.orderManagement.pagination.page || 1 });
                return;
            }

            if (managedOrderToggleEditButton) {
                await toggleManagedOrderEditor(managedOrderToggleEditButton.dataset.managedOrderToggleEdit);
                return;
            }

            if (managedOrderAddItemButton) {
                addManagedOrderEditorItem(managedOrderAddItemButton.dataset.orderId);
                return;
            }

            if (managedOrderRemoveItemButton) {
                removeManagedOrderEditorItem(managedOrderRemoveItemButton.dataset.orderId, managedOrderRemoveItemButton.dataset.managedOrderRemoveItem);
                return;
            }

            if (managedOrderSaveButton) {
                setMessage(dashboardMessage, 'Сохраняем заказ...');
                try {
                    await saveManagedOrder(managedOrderSaveButton.dataset.managedOrderSave);
                    setMessage(dashboardMessage, 'Заказ обновлён', 'ok');
                } catch (error) {
                    setMessage(dashboardMessage, error.message, 'error');
                }
                return;
            }

            if (managedOrderSaveStatusButton) {
                setMessage(dashboardMessage, 'Обновляем статус заказа...');
                try {
                    await saveManagedOrderStatus(managedOrderSaveStatusButton.dataset.managedOrderSaveStatus);
                    setMessage(dashboardMessage, 'Статус заказа обновлён', 'ok');
                } catch (error) {
                    setMessage(dashboardMessage, error.message, 'error');
                }
                return;
            }

            if (contactsTypeButton) {
                state.contactsView.type = contactsTypeButton.dataset.contactsType;
                await loadContactsPage({ page: 1 });
                return;
            }

            if (contactsSearchSubmitButton) {
                await loadContactsPage({ page: 1 });
                return;
            }

            if (contactsPageButton) {
                await loadContactsPage({ page: Number(contactsPageButton.dataset.contactsPage) });
                return;
            }

            if (refreshChatButton) {
                setMessage(dashboardMessage, 'Обновляем чат...');
                try {
                    await loadMessages();
                    setMessage(dashboardMessage, 'Чат обновлен', 'ok');
                } catch (error) {
                    setMessage(dashboardMessage, error.message, 'error');
                }
                return;
            }

            if (editButton) {
                beginEdit(editButton.dataset.edit, Number(editButton.dataset.id));
                return;
            }

            if (cancelButton) {
                cancelEdit(cancelButton.dataset.cancelEdit, Number(cancelButton.dataset.id));
                return;
            }

            if (activateButton) {
                setMessage(dashboardMessage, 'Активируем пользователя...');
                try {
                    await activateUser(Number(activateButton.dataset.activateUser));
                    await loadDashboardData();
                    setMessage(dashboardMessage, 'Пользователь активирован', 'ok');
                } catch (error) {
                    setMessage(dashboardMessage, error.message, 'error');
                }
            }
        });

        document.addEventListener('input', (event) => {
            const orderMetaField = event.target.closest('[data-order-meta-field]');
            if (orderMetaField) {
                updateOrderDraftMeta(orderMetaField.dataset.orderMetaField, orderMetaField.value);
                return;
            }

            const orderImportRaw = event.target.closest('[data-order-import-raw]');
            if (orderImportRaw) {
                updateOrderImportRawText(orderImportRaw.value);
                return;
            }

            const managedOrdersFilter = event.target.closest('[data-managed-orders-filter]');
            if (managedOrdersFilter) {
                updateManagedOrderFilter(managedOrdersFilter.dataset.managedOrdersFilter, managedOrdersFilter.value);
                return;
            }

            const contactsSearchInput = event.target.closest('[data-contacts-search]');
            if (contactsSearchInput) {
                updateContactsSearch(contactsSearchInput.value);
                return;
            }

            const managedOrderMeta = event.target.closest('[data-managed-order-meta]');
            if (managedOrderMeta) {
                updateManagedOrderEditorMeta(managedOrderMeta.dataset.orderId, managedOrderMeta.dataset.managedOrderMeta, managedOrderMeta.value);
                return;
            }

            const managedOrderItemField = event.target.closest('[data-managed-order-item-field]');
            if (managedOrderItemField) {
                updateManagedOrderEditorItemField(managedOrderItemField.dataset.orderId, managedOrderItemField.dataset.itemKey, managedOrderItemField.dataset.managedOrderItemField, managedOrderItemField.value);
                return;
            }

            const orderItemSearchInput = event.target.closest('[data-order-item-search-input]');
            if (orderItemSearchInput) {
                scheduleOrderItemProductSearch(orderItemSearchInput.dataset.orderItemSearchInput, orderItemSearchInput.value);
                return;
            }

            const orderItemField = event.target.closest('[data-order-item-field]');
            if (orderItemField) {
                updateOrderDraftItemField(orderItemField.dataset.itemKey, orderItemField.dataset.orderItemField, orderItemField.value);
                return;
            }

            const singleProductSearchInput = event.target.closest('[data-single-product-search-input]');
            if (singleProductSearchInput) {
                scheduleSingleDocumentProductSearch(singleProductSearchInput.dataset.singleProductSearchInput, singleProductSearchInput.value);
                return;
            }

            const inventoryForm = event.target.closest('form[data-document-form="inventory"]');
            if (inventoryForm && (event.target.name === 'product_article' || event.target.name === 'product_name')) {
                const searchState = getSingleProductSearchState('inventory');
                if (searchState?.selectedProduct) {
                    const articleInput = inventoryForm.querySelector('input[name="product_article"]');
                    const nameInput = inventoryForm.querySelector('input[name="product_name"]');
                    const matchesSelected = articleInput?.value === (searchState.selectedProduct.product_article || '')
                        && nameInput?.value === (searchState.selectedProduct.product_name || '');
                    if (!matchesSelected) {
                        searchState.selectedProduct = null;
                        searchState.query = '';
                        searchState.results = [];
                        renderSingleDocumentProductSearchUI('inventory');
                    }
                }
                return;
            }

            const registrationForm = event.target.closest('form[data-document-form="productRegistration"]');
            if (registrationForm && (event.target.name === 'product_article' || event.target.name === 'product_name')) {
                const searchState = getSingleProductSearchState('productRegistration');
                if (searchState?.selectedProduct) {
                    const articleInput = registrationForm.querySelector('input[name="product_article"]');
                    const nameInput = registrationForm.querySelector('input[name="product_name"]');
                    const matchesSelected = articleInput?.value === (searchState.selectedProduct.product_article || '')
                        && nameInput?.value === (searchState.selectedProduct.product_name || '');
                    if (!matchesSelected) {
                        searchState.selectedProduct = null;
                        searchState.query = '';
                        searchState.results = [];
                        renderSingleDocumentProductSearchUI('productRegistration');
                    }
                }
            }
        });

        document.addEventListener('change', (event) => {
            const auditDateInput = event.target.closest('[data-audit-date-input]');
            if (auditDateInput) {
                state.auditSelectedDate = auditDateInput.value || getTodayDateValue();
                void loadAuditEvents();
                return;
            }

            const managedOrderStatusSelect = event.target.closest('[data-managed-order-status-select]');
            if (managedOrderStatusSelect) {
                updateManagedOrderStatusDraft(managedOrderStatusSelect.dataset.managedOrderStatusSelect, managedOrderStatusSelect.value);
                return;
            }

            const managedOrdersFilter = event.target.closest('[data-managed-orders-filter]');
            if (managedOrdersFilter) {
                updateManagedOrderFilter(managedOrdersFilter.dataset.managedOrdersFilter, managedOrdersFilter.value);
                return;
            }

            const managedOrderMeta = event.target.closest('[data-managed-order-meta]');
            if (managedOrderMeta) {
                updateManagedOrderEditorMeta(managedOrderMeta.dataset.orderId, managedOrderMeta.dataset.managedOrderMeta, managedOrderMeta.value);
                return;
            }

            const managedOrderItemField = event.target.closest('[data-managed-order-item-field]');
            if (managedOrderItemField) {
                updateManagedOrderEditorItemField(managedOrderItemField.dataset.orderId, managedOrderItemField.dataset.itemKey, managedOrderItemField.dataset.managedOrderItemField, managedOrderItemField.value);
                return;
            }

            const orderMetaField = event.target.closest('[data-order-meta-field]');
            if (orderMetaField) {
                updateOrderDraftMeta(orderMetaField.dataset.orderMetaField, orderMetaField.value);
                return;
            }

            const orderItemField = event.target.closest('[data-order-item-field]');
            if (orderItemField) {
                updateOrderDraftItemField(orderItemField.dataset.itemKey, orderItemField.dataset.orderItemField, orderItemField.value);
            }
        });

        loginForm.addEventListener('submit', async (event) => {
            event.preventDefault();
            const formData = new FormData(loginForm);
            setMessage(loginMessage, 'Проверяем доступ...');

            try {
                await loginAsAdmin(formData.get('login'), formData.get('password'));
                setMessage(loginMessage, '');
                setMessage(dashboardMessage, 'Вход выполнен', 'ok');
            } catch (error) {
                clearSession();
                showLogin();
                setMessage(loginMessage, error.message, 'error');
            }
        });

        bootstrapForm.addEventListener('submit', async (event) => {
            event.preventDefault();
            const formData = new FormData(bootstrapForm);
            setMessage(loginMessage, 'Создаём первого администратора...');

            try {
                await bootstrapAdmin(formData);
                bootstrapForm.reset();
                document.getElementById('bootstrap-age').value = '30';
                setMessage(loginMessage, '');
                setMessage(dashboardMessage, 'Первый администратор создан', 'ok');
            } catch (error) {
                clearSession();
                try {
                    await loadSetupStatus();
                } catch (setupError) {
                    setMessage(loginMessage, setupError.message, 'error');
                    return;
                }
                showLogin();
                setMessage(loginMessage, error.message, 'error');
            }
        });

        document.getElementById('logout-button').addEventListener('click', async () => {
            clearSession();
            try {
                await loadSetupStatus();
            } catch (error) {
                setMessage(loginMessage, error.message, 'error');
            }
            showLogin();
            setMessage(loginMessage, 'Сессия завершена', 'ok');
            setMessage(dashboardMessage, '');
        });

        document.getElementById('refresh-button').addEventListener('click', async () => {
            setMessage(dashboardMessage, 'Обновляем данные...');
            try {
                await loadDashboardData();
                if (state.activeMenu === 'orders') {
                    await loadOrderManagementPage({ page: state.orderManagement.pagination.page || 1, silent: true });
                }
                if (state.activeMenu === 'counterparties') {
                    await loadContactsPage({ page: state.contactsView.pagination.page || 1, silent: true });
                }
                setMessage(dashboardMessage, 'Данные актуализированы', 'ok');
            } catch (error) {
                setMessage(dashboardMessage, error.message, 'error');
            }
        });

        document.getElementById('health-check-button').addEventListener('click', async () => {
            setMessage(loginMessage, 'Проверяем backend...');
            try {
                await checkBackendHealth();
                await loadSetupStatus();
                setMessage(loginMessage, 'Backend и database доступны', 'ok');
            } catch (error) {
                setMessage(loginMessage, error.message, 'error');
            }
        });

        document.getElementById('bootstrap-health-check-button').addEventListener('click', async () => {
            setMessage(loginMessage, 'Проверяем backend...');
            try {
                await checkBackendHealth();
                await loadSetupStatus();
                setMessage(loginMessage, 'Backend и database доступны', 'ok');
            } catch (error) {
                setMessage(loginMessage, error.message, 'error');
            }
        });

        document.getElementById('refresh-setup-button').addEventListener('click', async () => {
            setMessage(loginMessage, 'Обновляем setup status...');
            try {
                await loadSetupStatus();
                setMessage(loginMessage, isBootstrapRequired() ? 'Система ждёт первого администратора' : 'Система уже инициализирована', 'ok');
            } catch (error) {
                setMessage(loginMessage, error.message, 'error');
            }
        });

        document.getElementById('bootstrap-cancel-button').addEventListener('click', async () => {
            try {
                await loadSetupStatus();
                setMessage(loginMessage, isBootstrapRequired() ? 'На пустой базе доступен только bootstrap первого администратора' : '', isBootstrapRequired() ? '' : '');
            } catch (error) {
                setMessage(loginMessage, error.message, 'error');
            }
        });

        ensureAdminSession();
