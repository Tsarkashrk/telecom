import { useEffect, useMemo, useState } from 'react'
import { authApi, exportInvoices, invoiceApi, publicApi, subscriptionApi } from './api'

const initialRegister = {
  username: '',
  email: '',
  phone: '',
  password: '',
}

const initialLogin = {
  username: '',
  password: '',
}

const customerNav = [
  { id: 'overview', label: 'Обзор' },
  { id: 'tariffs', label: 'Тарифы' },
  { id: 'subscriptions', label: 'Подписки' },
  { id: 'billing', label: 'Биллинг' },
  { id: 'security', label: 'Безопасность' },
]

function formatMoney(value) {
  return new Intl.NumberFormat('ru-RU', {
    style: 'currency',
    currency: 'KZT',
    maximumFractionDigits: 2,
  }).format(Number(value || 0))
}

function formatDate(value) {
  if (!value) return '—'
  return new Intl.DateTimeFormat('ru-RU', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value))
}

function getInvoiceTone(status) {
  if (status === 'paid') return 'success'
  if (status === 'pending') return 'warning'
  if (status === 'overdue') return 'danger'
  return 'neutral'
}

function getSubscriptionTone(status) {
  if (status === 'active') return 'success'
  if (status === 'pending_payment') return 'warning'
  return 'neutral'
}

function validateRegisterForm(form) {
  if (!/^[a-zA-Z0-9_.-]{3,50}$/.test(form.username.trim())) {
    return 'Имя пользователя должно содержать 3-50 символов: буквы, цифры, ., _, -'
  }
  if (!/^\S+@\S+\.\S+$/.test(form.email.trim())) {
    return 'Введите корректный email'
  }
  if (form.phone.replace(/[^\d+]/g, '').length < 10) {
    return 'Введите корректный номер телефона'
  }
  if (form.password.length < 8) {
    return 'Пароль должен содержать минимум 8 символов'
  }
  return ''
}

function downloadBlob({ blob, filename }) {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}

function EmptyState({ title, text, actionLabel, onAction }) {
  return (
    <div className="empty-state">
      <h3>{title}</h3>
      <p>{text}</p>
      {actionLabel ? (
        <button className="secondary-button" type="button" onClick={onAction}>
          {actionLabel}
        </button>
      ) : null}
    </div>
  )
}

function StatCard({ label, value, hint, tone = 'default' }) {
  return (
    <article className={`stat-card ${tone}`}>
      <span>{label}</span>
      <strong>{value}</strong>
      <small>{hint}</small>
    </article>
  )
}

function InfoRow({ label, value }) {
  return (
    <div className="info-row">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  )
}

function SectionTitle({ title, text, actions }) {
  return (
    <div className="section-heading">
      <div>
        <h3>{title}</h3>
        {text ? <p>{text}</p> : null}
      </div>
      {actions ? <div className="quick-actions">{actions}</div> : null}
    </div>
  )
}

function FilterInput({ value, onChange, placeholder }) {
  return (
    <input
      className="toolbar-input"
      value={value}
      onChange={(event) => onChange(event.target.value)}
      placeholder={placeholder}
    />
  )
}

function DetailCard({ title, children, tone = 'default' }) {
  return (
    <article className={`panel-card detail-card ${tone}`}>
      <h3>{title}</h3>
      {children}
    </article>
  )
}

function RolePill({ role }) {
  return <span className={`role-pill role-${role}`}>{role}</span>
}

export default function App() {
  const [authMode, setAuthMode] = useState('login')
  const [registerForm, setRegisterForm] = useState(initialRegister)
  const [loginForm, setLoginForm] = useState(initialLogin)
  const [activeTab, setActiveTab] = useState('overview')
  const [statusMessage, setStatusMessage] = useState('')
  const [statusType, setStatusType] = useState('info')
  const [isBusy, setIsBusy] = useState(false)
  const [user, setUser] = useState(null)
  const [tariffs, setTariffs] = useState([])
  const [subscriptions, setSubscriptions] = useState([])
  const [invoices, setInvoices] = useState([])
  const [serviceInfo, setServiceInfo] = useState(null)
  const [serviceHealth, setServiceHealth] = useState(null)
  const [selectedInvoiceStatus, setSelectedInvoiceStatus] = useState(null)
  const [selectedSubscription, setSelectedSubscription] = useState(null)
  const [invoiceSearch, setInvoiceSearch] = useState('')
  const [subscriptionFilter, setSubscriptionFilter] = useState('all')
  const [tariffSearch, setTariffSearch] = useState('')
  const [operatorUserId, setOperatorUserId] = useState('')
  const [operatorSubscriptions, setOperatorSubscriptions] = useState([])
  const [operatorInvoices, setOperatorInvoices] = useState([])
  const [operatorLoading, setOperatorLoading] = useState(false)
  const [adminHealthLoading, setAdminHealthLoading] = useState(false)

  const isOperator = user?.role === 'operator' || user?.role === 'admin'
  const isAdmin = user?.role === 'admin'

  const displayedNav = useMemo(() => {
    const items = [...customerNav]
    if (isOperator) {
      items.push({ id: 'operator', label: 'Оператор' })
    }
    if (isAdmin) {
      items.push({ id: 'admin', label: 'Админ' })
    }
    return items
  }, [isAdmin, isOperator])

  const filteredTariffs = useMemo(() => {
    const query = tariffSearch.trim().toLowerCase()
    if (!query) return tariffs
    return tariffs.filter((tariff) => {
      return [tariff.name, tariff.description, String(tariff.id)].join(' ').toLowerCase().includes(query)
    })
  }, [tariffSearch, tariffs])

  const filteredSubscriptions = useMemo(() => {
    return subscriptions.filter((subscription) => {
      const matchesStatus = subscriptionFilter === 'all' || subscription.status === subscriptionFilter
      return matchesStatus
    })
  }, [subscriptionFilter, subscriptions])

  const filteredInvoices = useMemo(() => {
    const query = invoiceSearch.trim().toLowerCase()
    if (!query) return invoices
    return invoices.filter((invoice) => {
      return [invoice.id, invoice.subscription_id, invoice.status, invoice.amount].join(' ').toLowerCase().includes(query)
    })
  }, [invoiceSearch, invoices])

  const metrics = useMemo(() => {
    const activeSubscriptions = subscriptions.filter((item) => item.status === 'active' || item.status === 'pending_payment').length
    const paidInvoices = invoices.filter((item) => item.status === 'paid').length
    const unpaidInvoices = invoices.filter((item) => item.status !== 'paid').length
    const totalDue = invoices.filter((item) => item.status !== 'paid').reduce((sum, item) => sum + item.amount, 0)
    return { activeSubscriptions, paidInvoices, unpaidInvoices, totalDue }
  }, [subscriptions, invoices])

  const nextPendingInvoice = useMemo(() => {
    return [...invoices]
      .filter((invoice) => invoice.status === 'pending')
      .sort((left, right) => new Date(left.due_date) - new Date(right.due_date))[0]
  }, [invoices])

  const currentSubscription = useMemo(() => {
    return subscriptions.find((item) => item.status === 'active') || subscriptions.find((item) => item.status === 'pending_payment') || null
  }, [subscriptions])

  const operatorMetrics = useMemo(() => {
    const pendingCount = operatorInvoices.filter((invoice) => invoice.status === 'pending').length
    const activeCount = operatorSubscriptions.filter((subscription) => subscription.status === 'active').length
    const dueTotal = operatorInvoices.filter((invoice) => invoice.status !== 'paid').reduce((sum, invoice) => sum + invoice.amount, 0)
    return { pendingCount, activeCount, dueTotal }
  }, [operatorInvoices, operatorSubscriptions])

  async function loadServiceSnapshot() {
    try {
      const [rootData, healthData] = await Promise.all([publicApi.getRoot(), publicApi.getHealth()])
      setServiceInfo(rootData)
      setServiceHealth(healthData)
    } catch (error) {
      setServiceInfo(null)
      setServiceHealth({ status: 'unavailable', detail: error.message })
    }
  }

  async function loadWorkspaceData() {
    const [tariffData, subscriptionData, invoiceData] = await Promise.all([subscriptionApi.getTariffs(), subscriptionApi.getSubscriptions(), invoiceApi.getInvoices()])
    setTariffs(tariffData)
    setSubscriptions(subscriptionData)
    setInvoices(invoiceData)
  }

  async function bootstrap() {
    await loadServiceSnapshot()
    try {
      const currentUser = await authApi.me()
      setUser(currentUser)
      await loadWorkspaceData()
    } catch {
      setUser(null)
    }
  }

  useEffect(() => {
    bootstrap()
  }, [])

  function showStatus(message, type = 'info') {
    setStatusMessage(message)
    setStatusType(type)
  }

  async function handleLogin(event) {
    event.preventDefault()
    setIsBusy(true)
    try {
      await authApi.login(loginForm)
      const currentUser = await authApi.me()
      setUser(currentUser)
      await loadWorkspaceData()
      showStatus('Вход выполнен. Рабочее пространство роли синхронизировано.', 'success')
      setLoginForm(initialLogin)
      setActiveTab('overview')
    } catch (error) {
      showStatus(error.message, 'error')
    } finally {
      setIsBusy(false)
    }
  }

  async function handleRegister(event) {
    event.preventDefault()
    const validationMessage = validateRegisterForm(registerForm)
    if (validationMessage) {
      showStatus(validationMessage, 'error')
      return
    }

    setIsBusy(true)
    try {
      await authApi.register(registerForm)
      showStatus('Регистрация выполнена. Теперь можно войти в систему.', 'success')
      setRegisterForm(initialRegister)
      setAuthMode('login')
    } catch (error) {
      showStatus(error.message, 'error')
    } finally {
      setIsBusy(false)
    }
  }

  async function handleActivateTariff(tariffId) {
    setIsBusy(true)
    try {
      await subscriptionApi.activateTariff(tariffId)
      await loadWorkspaceData()
      setActiveTab('subscriptions')
      showStatus('Тариф активирован в режиме предоплаты. Сформированы подписка и счет.', 'success')
    } catch (error) {
      showStatus(error.message, 'error')
    } finally {
      setIsBusy(false)
    }
  }

  async function handlePayInvoice(invoiceId) {
    setIsBusy(true)
    try {
      await invoiceApi.payInvoice(invoiceId)
      await loadWorkspaceData()
      if (selectedInvoiceStatus?.invoice_id === invoiceId) {
        const status = await invoiceApi.getInvoiceStatus(invoiceId)
        setSelectedInvoiceStatus(status)
      }
      showStatus('Счет оплачен, подписка переведена в активное состояние.', 'success')
    } catch (error) {
      showStatus(error.message, 'error')
    } finally {
      setIsBusy(false)
    }
  }

  async function handleExport(format) {
    setIsBusy(true)
    try {
      const file = await exportInvoices(format)
      downloadBlob(file)
      showStatus(`Экспорт ${format.toUpperCase()} подготовлен и скачан.`, 'success')
    } catch (error) {
      showStatus(error.message, 'error')
    } finally {
      setIsBusy(false)
    }
  }

  async function handleLogout() {
    setIsBusy(true)
    try {
      await authApi.logout()
      setUser(null)
      setTariffs([])
      setSubscriptions([])
      setInvoices([])
      setSelectedInvoiceStatus(null)
      setSelectedSubscription(null)
      setOperatorInvoices([])
      setOperatorSubscriptions([])
      showStatus('Сеанс завершен.', 'info')
    } finally {
      setIsBusy(false)
    }
  }

  async function handleInvoiceStatus(invoiceId) {
    setIsBusy(true)
    try {
      const status = await invoiceApi.getInvoiceStatus(invoiceId)
      setSelectedInvoiceStatus(status)
      showStatus(`Статус счета #${invoiceId} обновлен.`, 'info')
    } catch (error) {
      showStatus(error.message, 'error')
    } finally {
      setIsBusy(false)
    }
  }

  async function handleSubscriptionDetails(subscriptionId) {
    setIsBusy(true)
    try {
      const details = await subscriptionApi.getSubscription(subscriptionId)
      setSelectedSubscription(details)
      showStatus(`Подробности по подписке #${subscriptionId} загружены.`, 'info')
    } catch (error) {
      showStatus(error.message, 'error')
    } finally {
      setIsBusy(false)
    }
  }

  async function handleOperatorLookup(event) {
    event.preventDefault()
    if (!operatorUserId.trim()) {
      showStatus('Укажите ID пользователя для операторского просмотра.', 'error')
      return
    }

    setOperatorLoading(true)
    try {
      const [subs, invs] = await Promise.all([subscriptionApi.getSubscriptionsByUser(operatorUserId.trim()), invoiceApi.getInvoicesByUser(operatorUserId.trim())])
      setOperatorSubscriptions(subs)
      setOperatorInvoices(invs)
      showStatus(`Данные клиента #${operatorUserId.trim()} загружены.`, 'success')
    } catch (error) {
      showStatus(error.message, 'error')
    } finally {
      setOperatorLoading(false)
    }
  }

  async function handleAdminHealthRefresh() {
    setAdminHealthLoading(true)
    try {
      await loadServiceSnapshot()
      showStatus('Состояние backend и health-check обновлено.', 'success')
    } catch (error) {
      showStatus(error.message, 'error')
    } finally {
      setAdminHealthLoading(false)
    }
  }

  if (!user) {
    return (
      <main className="shell auth-shell">
        <section className="auth-hero">
          <div className="eyebrow">Secure SDLC + OWASP Top 10</div>
          <h1>Telecom Secure MVP</h1>
          <p>Интерфейс для защищенного MVP телеком-платформы: регистрация, аутентификация, тарифы, подписки, биллинг и роль-ориентированные рабочие пространства.</p>

          <div className="hero-grid">
            <StatCard label="Customer" value="Self-service" hint="Тарифы, подписки, оплата" />
            <StatCard label="Operator" value="Support" hint="Поиск клиента, счета, статусы" />
            <StatCard label="Admin" value="Control" hint="Health, RBAC, безопасность" />
          </div>
        </section>

        <section className="auth-card">
          <div className="auth-tabs">
            <button className={authMode === 'login' ? 'active' : ''} onClick={() => setAuthMode('login')} type="button">
              Вход
            </button>
            <button className={authMode === 'register' ? 'active' : ''} onClick={() => setAuthMode('register')} type="button">
              Регистрация
            </button>
          </div>

          {authMode === 'login' ? (
            <form className="form-grid" onSubmit={handleLogin}>
              <label>
                Имя пользователя
                <input value={loginForm.username} onChange={(event) => setLoginForm((prev) => ({ ...prev, username: event.target.value }))} placeholder="testuser" />
              </label>
              <label>
                Пароль
                <input type="password" value={loginForm.password} onChange={(event) => setLoginForm((prev) => ({ ...prev, password: event.target.value }))} placeholder="Введите пароль" />
              </label>
              <button className="primary-button" disabled={isBusy} type="submit">
                {isBusy ? 'Проверка...' : 'Войти'}
              </button>
            </form>
          ) : (
            <form className="form-grid" onSubmit={handleRegister}>
              <label>
                Имя пользователя
                <input value={registerForm.username} onChange={(event) => setRegisterForm((prev) => ({ ...prev, username: event.target.value }))} placeholder="newuser" />
              </label>
              <label>
                Email
                <input type="email" value={registerForm.email} onChange={(event) => setRegisterForm((prev) => ({ ...prev, email: event.target.value }))} placeholder="user@example.com" />
              </label>
              <label>
                Телефон
                <input value={registerForm.phone} onChange={(event) => setRegisterForm((prev) => ({ ...prev, phone: event.target.value }))} placeholder="+7 (777) 123-45-67" />
              </label>
              <label>
                Пароль
                <input type="password" value={registerForm.password} onChange={(event) => setRegisterForm((prev) => ({ ...prev, password: event.target.value }))} placeholder="С буквой, цифрой и спецсимволом" />
              </label>
              <button className="primary-button" disabled={isBusy} type="submit">
                {isBusy ? 'Создание...' : 'Создать аккаунт'}
              </button>
            </form>
          )}

          {statusMessage ? <div className={`status-banner ${statusType}`}>{statusMessage}</div> : null}
        </section>
      </main>
    )
  }

  return (
    <main className="shell app-shell">
      <header className="topbar">
        <div>
          <div className="eyebrow">Telecom Secure MVP</div>
          <h1>{isAdmin ? 'Административная консоль' : isOperator ? 'Операторская и клиентская панель' : 'Кабинет абонента'}</h1>
        </div>
        <div className="topbar-actions">
          <div className="user-badge">
            <span>{user.username}</span>
            <strong><RolePill role={user.role} /></strong>
          </div>
          <button className="ghost-button" onClick={handleLogout} type="button">
            Выйти
          </button>
        </div>
      </header>

      <section className="hero-panel">
        <div className="hero-copy">
          <h2>{isAdmin ? 'Контролируйте доступ, состояние API и пользовательские операции' : isOperator ? 'Поддерживайте клиентов и контролируйте их подписки и счета' : 'Управляйте тарифом, подпиской и оплатой в одном потоке'}</h2>
          <p>
            {isAdmin
              ? 'Администратор видит состояние сервиса, матрицу ролей, безопасные сценарии и может использовать операторские инструменты для проверки клиентского пути.'
              : isOperator
                ? 'Оператору доступны собственные данные и отдельная рабочая зона для поиска клиента по ID, просмотра подписок и контроля неоплаченных счетов.'
                : 'Customer-сценарий покрывает весь путь: вход, выбор тарифа, создание счета, оплату и активацию услуги без выхода из интерфейса.'}
          </p>
        </div>
        <div className="hero-grid">
          <StatCard label="Подписок" value={metrics.activeSubscriptions} hint="Ваши активные и pending" />
          <StatCard label="Неоплачено" value={metrics.unpaidInvoices} hint="Счета, требующие действия" tone={metrics.unpaidInvoices ? 'warning' : 'success'} />
          <StatCard label="Оплачено" value={metrics.paidInvoices} hint="Успешно завершенные оплаты" />
        </div>
      </section>

      <nav className="app-nav">
        {displayedNav.map((item) => (
          <button key={item.id} className={activeTab === item.id ? 'active' : ''} onClick={() => setActiveTab(item.id)} type="button">
            {item.label}
          </button>
        ))}
      </nav>

      {statusMessage ? <div className={`status-banner ${statusType}`}>{statusMessage}</div> : null}

      {activeTab === 'overview' ? (
        <section className="panel-stack">
          <section className="card-grid dashboard-grid">
            <StatCard label="Роль" value={user.role} hint="Текущая модель доступа" />
            <StatCard label="Сумма к оплате" value={formatMoney(metrics.totalDue)} hint="Только неоплаченные счета" tone={metrics.totalDue ? 'warning' : 'success'} />
            <StatCard label="Backend" value={serviceHealth?.status || 'unknown'} hint={`API ${serviceInfo?.version || '—'}`} tone={serviceHealth?.status === 'healthy' ? 'success' : 'danger'} />
          </section>

          <section className="panel-grid two-columns">
            <article className="panel-card accent-card">
              <h3>Профиль и доступ</h3>
              <div className="info-grid">
                <InfoRow label="Пользователь" value={user.username} />
                <InfoRow label="Email" value={user.email} />
                <InfoRow label="Телефон" value={user.phone} />
                <InfoRow label="Статус" value={user.is_active ? 'active' : 'inactive'} />
                <InfoRow label="Создан" value={formatDate(user.created_at)} />
                <InfoRow label="Роль" value={user.role} />
              </div>
            </article>

            <article className="panel-card">
              <h3>Текущая ситуация</h3>
              {currentSubscription ? (
                <div className="stack-sm">
                  <div className="card-meta">
                    <span className={`status-pill ${getSubscriptionTone(currentSubscription.status)}`}>{currentSubscription.status}</span>
                    <span>Подписка #{currentSubscription.id}</span>
                  </div>
                  <p>
                    Текущий тариф: <strong>{currentSubscription.tariff_plan?.name || 'не определен'}</strong>
                  </p>
                  <ul className="feature-list">
                    <li>Следующий биллинг: {formatDate(currentSubscription.next_billing_date)}</li>
                    <li>Лимит интернета: {currentSubscription.tariff_plan?.data_limit_gb ?? '—'} ГБ</li>
                    <li>Минуты: {currentSubscription.tariff_plan?.minutes_limit ?? '—'}</li>
                  </ul>
                </div>
              ) : (
                <EmptyState title="Нет активного тарифа" text="Начните с выбора тарифного плана, чтобы сформировать подписку." actionLabel="Открыть тарифы" onAction={() => setActiveTab('tariffs')} />
              )}
            </article>
          </section>

          <section className="panel-grid two-columns">
            <article className="panel-card">
              <h3>Ближайшее действие</h3>
              {nextPendingInvoice ? (
                <div className="stack-sm">
                  <p>
                    Счет <strong>#{nextPendingInvoice.id}</strong> ожидает оплату до {formatDate(nextPendingInvoice.due_date)}.
                  </p>
                  <p className="metric-inline">{formatMoney(nextPendingInvoice.amount)}</p>
                  <div className="quick-actions">
                    <button className="primary-button" type="button" disabled={isBusy} onClick={() => handlePayInvoice(nextPendingInvoice.id)}>
                      Оплатить сейчас
                    </button>
                    <button className="secondary-button" type="button" disabled={isBusy} onClick={() => handleInvoiceStatus(nextPendingInvoice.id)}>
                      Проверить статус
                    </button>
                  </div>
                </div>
              ) : (
                <EmptyState title="Срочных действий нет" text="Все счета оплачены или пока не выставлены." />
              )}
            </article>

            <article className="panel-card">
              <h3>Рабочие возможности роли</h3>
              <ul className="feature-list">
                <li>Customer: выбор тарифа, просмотр подписок, оплата счетов, экспорт данных.</li>
                {isOperator ? <li>Operator: поиск клиента по ID, контроль его подписок и задолженности.</li> : null}
                {isAdmin ? <li>Admin: мониторинг health-check, контроль ролей и безопасной конфигурации интерфейса.</li> : null}
              </ul>
            </article>
          </section>
        </section>
      ) : null}

      {activeTab === 'tariffs' ? (
        <section className="panel-stack">
          <article className="panel-card">
            <SectionTitle
              title="Доступные тарифы"
              text="Подберите план под сценарий клиента и сразу запустите prepaid-активацию."
              actions={<FilterInput value={tariffSearch} onChange={setTariffSearch} placeholder="Поиск по названию, описанию или ID" />}
            />
          </article>

          <section className="card-grid">
            {filteredTariffs.length ? (
              filteredTariffs.map((tariff) => {
                const isCurrentTariff = currentSubscription?.tariff_id === tariff.id
                return (
                  <article className={`tariff-card ${isCurrentTariff ? 'is-highlighted' : ''}`} key={tariff.id}>
                    <div className="tariff-head">
                      <span className="tariff-chip">Тариф #{tariff.id}</span>
                      <strong>{formatMoney(tariff.monthly_price)}</strong>
                    </div>
                    <h3>{tariff.name}</h3>
                    <p>{tariff.description || 'Оптимизированный пакет услуг для связи.'}</p>
                    <div className="tariff-metrics">
                      <span>{tariff.data_limit_gb} ГБ</span>
                      <span>{tariff.minutes_limit} мин</span>
                      <span>{tariff.sms_limit} SMS</span>
                    </div>
                    <button className="primary-button" disabled={isBusy || isCurrentTariff} onClick={() => handleActivateTariff(tariff.id)} type="button">
                      {isCurrentTariff ? 'Текущий тариф' : 'Активировать'}
                    </button>
                  </article>
                )
              })
            ) : (
              <EmptyState title="Ничего не найдено" text="Измените поисковый запрос или дождитесь загрузки активных тарифов." onAction={() => setTariffSearch('')} actionLabel="Сбросить поиск" />
            )}
          </section>
        </section>
      ) : null}

      {activeTab === 'subscriptions' ? (
        <section className="panel-stack">
          <article className="panel-card">
            <SectionTitle
              title="Подписки"
              text="Просматривайте состояние подключения, активность и детали выбранного тарифа."
              actions={
                <div className="quick-actions compact-actions">
                  <button className={`chip-button ${subscriptionFilter === 'all' ? 'active' : ''}`} type="button" onClick={() => setSubscriptionFilter('all')}>
                    Все
                  </button>
                  <button className={`chip-button ${subscriptionFilter === 'active' ? 'active' : ''}`} type="button" onClick={() => setSubscriptionFilter('active')}>
                    Active
                  </button>
                  <button className={`chip-button ${subscriptionFilter === 'pending_payment' ? 'active' : ''}`} type="button" onClick={() => setSubscriptionFilter('pending_payment')}>
                    Pending
                  </button>
                </div>
              }
            />
          </article>

          <section className="panel-grid focus-layout">
            <div className="card-grid">
              {filteredSubscriptions.length ? (
                filteredSubscriptions.map((subscription) => (
                  <article className="panel-card subscription-card" key={subscription.id}>
                    <div className="card-meta">
                      <span className={`status-pill ${getSubscriptionTone(subscription.status)}`}>{subscription.status}</span>
                      <span>ID #{subscription.id}</span>
                    </div>
                    <h3>{subscription.tariff_plan?.name || 'Тариф'}</h3>
                    <p>Следующее списание: {formatDate(subscription.next_billing_date)}</p>
                    <ul className="feature-list">
                      <li>Статус активности: {subscription.is_active ? 'да' : 'нет'}</li>
                      <li>Трафик: {subscription.tariff_plan?.data_limit_gb ?? '-'} ГБ</li>
                      <li>Минуты: {subscription.tariff_plan?.minutes_limit ?? '-'}</li>
                    </ul>
                    <button className="secondary-button" type="button" disabled={isBusy} onClick={() => handleSubscriptionDetails(subscription.id)}>
                      Подробнее
                    </button>
                  </article>
                ))
              ) : (
                <EmptyState title="Подписок пока нет" text="Активируйте тариф, чтобы backend создал подписку и счет." actionLabel="Перейти к тарифам" onAction={() => setActiveTab('tariffs')} />
              )}
            </div>

            <DetailCard title="Выбранная подписка" tone="subtle">
              {selectedSubscription ? (
                <div className="info-grid">
                  <InfoRow label="ID" value={`#${selectedSubscription.id}`} />
                  <InfoRow label="Статус" value={selectedSubscription.status} />
                  <InfoRow label="Тариф" value={selectedSubscription.tariff_plan?.name || '—'} />
                  <InfoRow label="Активирована" value={formatDate(selectedSubscription.activation_date)} />
                  <InfoRow label="Следующий биллинг" value={formatDate(selectedSubscription.next_billing_date)} />
                  <InfoRow label="SMS" value={selectedSubscription.tariff_plan?.sms_limit ?? '—'} />
                </div>
              ) : (
                <p className="muted-text">Выберите карточку подписки, чтобы увидеть ее полные атрибуты.</p>
              )}
            </DetailCard>
          </section>
        </section>
      ) : null}

      {activeTab === 'billing' ? (
        <section className="panel-stack">
          <article className="panel-card">
            <SectionTitle
              title="Счета и экспорт"
              text="Проверяйте статусы, выполняйте оплату и выгружайте данные в CSV/JSON."
              actions={
                <>
                  <FilterInput value={invoiceSearch} onChange={setInvoiceSearch} placeholder="Поиск по ID, статусу, сумме или подписке" />
                  <button className="secondary-button" disabled={isBusy} onClick={() => handleExport('csv')} type="button">
                    Экспорт CSV
                  </button>
                  <button className="secondary-button" disabled={isBusy} onClick={() => handleExport('json')} type="button">
                    Экспорт JSON
                  </button>
                </>
              }
            />
          </article>

          <section className="panel-grid focus-layout">
            <div className="card-grid">
              {filteredInvoices.length ? (
                filteredInvoices.map((invoice) => (
                  <article className="panel-card invoice-card" key={invoice.id}>
                    <div className="card-meta">
                      <span className={`status-pill ${getInvoiceTone(invoice.status)}`}>{invoice.status}</span>
                      <span>Счет #{invoice.id}</span>
                    </div>
                    <h3>{formatMoney(invoice.amount)}</h3>
                    <p>Оплатить до {formatDate(invoice.due_date)}</p>
                    <ul className="feature-list">
                      <li>Подписка: #{invoice.subscription_id}</li>
                      <li>Период начала: {formatDate(invoice.billing_period_start)}</li>
                      <li>Создан: {formatDate(invoice.created_at)}</li>
                    </ul>
                    <div className="quick-actions split-actions">
                      <button className="secondary-button" disabled={isBusy} onClick={() => handleInvoiceStatus(invoice.id)} type="button">
                        Статус
                      </button>
                      <button className="primary-button" disabled={isBusy || invoice.status !== 'pending'} onClick={() => handlePayInvoice(invoice.id)} type="button">
                        {invoice.status === 'paid' ? 'Уже оплачен' : 'Оплатить'}
                      </button>
                    </div>
                  </article>
                ))
              ) : (
                <EmptyState title="Счета не найдены" text="После активации тарифа backend сформирует prepaid-счет." />
              )}
            </div>

            <DetailCard title="Оперативный статус счета" tone="subtle">
              {selectedInvoiceStatus ? (
                <div className="info-grid">
                  <InfoRow label="Invoice ID" value={`#${selectedInvoiceStatus.invoice_id}`} />
                  <InfoRow label="Статус" value={selectedInvoiceStatus.status} />
                  <InfoRow label="Сумма" value={formatMoney(selectedInvoiceStatus.amount)} />
                  <InfoRow label="Срок оплаты" value={formatDate(selectedInvoiceStatus.due_date)} />
                </div>
              ) : (
                <p className="muted-text">Нажмите «Статус» на нужном счете, чтобы получить свежие данные от backend.</p>
              )}
            </DetailCard>
          </section>
        </section>
      ) : null}

      {activeTab === 'security' ? (
        <section className="panel-grid two-columns">
          <article className="panel-card">
            <h3>Реализованные механизмы защиты</h3>
            <ul className="feature-list">
              <li>Хеширование паролей через bcrypt/passlib.</li>
              <li>Проверка токенов и ротация refresh token.</li>
              <li>Ограничение размера запросов и валидация входных данных.</li>
              <li>RBAC и owner-based authorization для счетов и подписок.</li>
              <li>Безопасное логирование входа, отказов и критичных действий.</li>
            </ul>
          </article>

          <article className="panel-card">
            <h3>Роль-ориентированная модель UX</h3>
            <ul className="feature-list">
              <li>Customer видит только собственные сущности и действия оплаты.</li>
              <li>Operator получает отдельную рабочую зону для обслуживания клиента по `userId`.</li>
              <li>Admin получает health-check и системный обзор без добавления небезопасных клиентских операций.</li>
              <li>Недоступные backend-функции не имитируются на клиенте и не маскируются под реальные права.</li>
            </ul>
          </article>
        </section>
      ) : null}

      {activeTab === 'operator' ? (
        <section className="panel-stack">
          <article className="panel-card">
            <SectionTitle
              title="Операторская рабочая зона"
              text="Поиск клиента по ID, анализ активных подписок и счетов, выявление задолженности."
            />
            <form className="operator-form" onSubmit={handleOperatorLookup}>
              <input value={operatorUserId} onChange={(event) => setOperatorUserId(event.target.value)} placeholder="Например: 1" />
              <button className="primary-button" disabled={operatorLoading} type="submit">
                {operatorLoading ? 'Загрузка...' : 'Загрузить данные'}
              </button>
            </form>
          </article>

          <section className="card-grid dashboard-grid">
            <StatCard label="Активные" value={operatorMetrics.activeCount} hint="Подписки клиента" />
            <StatCard label="Pending invoices" value={operatorMetrics.pendingCount} hint="Требуют оплаты" tone={operatorMetrics.pendingCount ? 'warning' : 'success'} />
            <StatCard label="К оплате" value={formatMoney(operatorMetrics.dueTotal)} hint="Неоплаченный баланс" />
          </section>

          <section className="panel-grid two-columns">
            <article className="panel-card">
              <h3>Подписки клиента</h3>
              {operatorSubscriptions.length ? (
                <div className="record-list">
                  {operatorSubscriptions.map((item) => (
                    <button key={item.id} className="record-row" type="button" onClick={() => handleSubscriptionDetails(item.id)}>
                      <span>#{item.id}</span>
                      <strong>{item.tariff_plan?.name || 'Тариф'}</strong>
                      <span className={`status-pill ${getSubscriptionTone(item.status)}`}>{item.status}</span>
                    </button>
                  ))}
                </div>
              ) : (
                <p className="muted-text">Данные еще не запрошены или по пользователю нет подписок.</p>
              )}
            </article>

            <article className="panel-card">
              <h3>Счета клиента</h3>
              {operatorInvoices.length ? (
                <div className="record-list">
                  {operatorInvoices.map((item) => (
                    <button key={item.id} className="record-row" type="button" onClick={() => handleInvoiceStatus(item.id)}>
                      <span>#{item.id}</span>
                      <strong>{formatMoney(item.amount)}</strong>
                      <span className={`status-pill ${getInvoiceTone(item.status)}`}>{item.status}</span>
                    </button>
                  ))}
                </div>
              ) : (
                <p className="muted-text">Данные еще не запрошены или у клиента нет счетов.</p>
              )}
            </article>
          </section>
        </section>
      ) : null}

      {activeTab === 'admin' ? (
        <section className="panel-stack">
          <article className="panel-card">
            <SectionTitle
              title="Системный обзор администратора"
              text="Безопасный мониторинг доступности API и контроль матрицы ролей без обхода backend-ограничений."
              actions={
                <button className="primary-button" type="button" disabled={adminHealthLoading} onClick={handleAdminHealthRefresh}>
                  {adminHealthLoading ? 'Обновление...' : 'Обновить health'}
                </button>
              }
            />
          </article>

          <section className="card-grid dashboard-grid">
            <StatCard label="Service" value={serviceInfo?.name || 'unknown'} hint="Корневой endpoint" />
            <StatCard label="Version" value={serviceInfo?.version || '—'} hint="Версия backend" />
            <StatCard label="Health" value={serviceHealth?.status || 'unknown'} hint="Результат /health" tone={serviceHealth?.status === 'healthy' ? 'success' : 'danger'} />
          </section>

          <section className="panel-grid two-columns">
            <article className="panel-card">
              <h3>Матрица ролей</h3>
              <div className="role-matrix">
                <div className="matrix-row">
                  <RolePill role="customer" />
                  <span>Собственные тарифы, подписки, счета, экспорт и оплата.</span>
                </div>
                <div className="matrix-row">
                  <RolePill role="operator" />
                  <span>Просмотр клиентских подписок и счетов по `userId` через защищенные API.</span>
                </div>
                <div className="matrix-row">
                  <RolePill role="admin" />
                  <span>Все возможности оператора плюс контроль состояния backend и политики доступа.</span>
                </div>
              </div>
            </article>

            <article className="panel-card">
              <h3>Наблюдаемость и hardening</h3>
              <ul className="feature-list">
                <li>JWT access/refresh flow не раскрывает чувствительные данные на клиенте.</li>
                <li>Frontend не хранит секреты внутреннего API и не вызывает внутренний биллинг endpoint напрямую.</li>
                <li>Админ-экран показывает только безопасные технические сведения: `name`, `version`, `health`.</li>
                <li>Операторские действия не расширяют backend-права и полностью зависят от RBAC на сервере.</li>
              </ul>
            </article>
          </section>
        </section>
      ) : null}
    </main>
  )
}
