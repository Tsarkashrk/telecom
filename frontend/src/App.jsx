import { useEffect, useMemo, useState } from "react";
import {
  authApi,
  exportInvoices,
  invoiceApi,
  subscriptionApi,
} from "./api";

const initialRegister = {
  username: "",
  email: "",
  phone: "",
  password: "",
};

const initialLogin = {
  username: "",
  password: "",
};

const navItems = [
  // { id: "overview", label: "Обзор" },
  { id: "tariffs", label: "Тарифы" },
  { id: "subscriptions", label: "Подписки" },
  { id: "billing", label: "Биллинг" },
  // { id: "security", label: "Безопасность" },
];

function formatMoney(value) {
  return new Intl.NumberFormat("ru-RU", {
    style: "currency",
    currency: "KZT",
    maximumFractionDigits: 2,
  }).format(value);
}

function formatDate(value) {
  return new Intl.DateTimeFormat("ru-RU", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function getInvoiceTone(status) {
  if (status === "paid") return "success";
  if (status === "pending") return "warning";
  return "neutral";
}

function validateRegisterForm(form) {
  if (!/^[a-zA-Z0-9_.-]{3,50}$/.test(form.username.trim())) {
    return "Имя пользователя должно содержать 3-50 символов: буквы, цифры, ., _, -";
  }
  if (!/^\S+@\S+\.\S+$/.test(form.email.trim())) {
    return "Введите корректный email";
  }
  if (form.phone.replace(/[^\d+]/g, "").length < 10) {
    return "Введите корректный номер телефона";
  }
  if (form.password.length < 8) {
    return "Пароль должен содержать минимум 8 символов";
  }
  return "";
}

function downloadBlob({ blob, filename }) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function EmptyState({ title, text }) {
  return (
    <div className="empty-state">
      <h3>{title}</h3>
      <p>{text}</p>
    </div>
  );
}

function StatCard({ label, value, hint }) {
  return (
    <article className="stat-card">
      <span>{label}</span>
      <strong>{value}</strong>
      <small>{hint}</small>
    </article>
  );
}

export default function App() {
  const [authMode, setAuthMode] = useState("login");
  const [registerForm, setRegisterForm] = useState(initialRegister);
  const [loginForm, setLoginForm] = useState(initialLogin);
  const [activeTab, setActiveTab] = useState("overview");
  const [statusMessage, setStatusMessage] = useState("");
  const [statusType, setStatusType] = useState("info");
  const [isBusy, setIsBusy] = useState(false);
  const [user, setUser] = useState(null);
  const [tariffs, setTariffs] = useState([]);
  const [subscriptions, setSubscriptions] = useState([]);
  const [invoices, setInvoices] = useState([]);
  const [operatorUserId, setOperatorUserId] = useState("");
  const [operatorSubscriptions, setOperatorSubscriptions] = useState([]);
  const [operatorInvoices, setOperatorInvoices] = useState([]);

  const isOperator = user?.role === "operator" || user?.role === "admin";
  const displayedNav = isOperator
    ? [...navItems, { id: "operator", label: "Оператор" }]
    : navItems;

  const metrics = useMemo(() => {
    const activeSubscriptions = subscriptions.filter(
      (item) => item.status === "active" || item.status === "pending_payment",
    ).length;
    const unpaidInvoices = invoices.filter((item) => item.status !== "paid").length;
    const totalDue = invoices
      .filter((item) => item.status !== "paid")
      .reduce((sum, item) => sum + item.amount, 0);

    return { activeSubscriptions, unpaidInvoices, totalDue };
  }, [subscriptions, invoices]);

  async function bootstrap() {
    try {
      const currentUser = await authApi.me();
      setUser(currentUser);
      await loadWorkspaceData();
    } catch {
      setUser(null);
    }
  }

  async function loadWorkspaceData() {
    const [tariffData, subscriptionData, invoiceData] = await Promise.all([
      subscriptionApi.getTariffs(),
      subscriptionApi.getSubscriptions(),
      invoiceApi.getInvoices(),
    ]);
    setTariffs(tariffData);
    setSubscriptions(subscriptionData);
    setInvoices(invoiceData);
  }

  useEffect(() => {
    bootstrap();
  }, []);

  function showStatus(message, type = "info") {
    setStatusMessage(message);
    setStatusType(type);
  }

  async function handleLogin(event) {
    event.preventDefault();
    setIsBusy(true);
    try {
      await authApi.login(loginForm);
      const currentUser = await authApi.me();
      setUser(currentUser);
      await loadWorkspaceData();
      showStatus("Вход выполнен. Панель синхронизирована с backend.", "success");
      setLoginForm(initialLogin);
    } catch (error) {
      showStatus(error.message, "error");
    } finally {
      setIsBusy(false);
    }
  }

  async function handleRegister(event) {
    event.preventDefault();
    const validationMessage = validateRegisterForm(registerForm);
    if (validationMessage) {
      showStatus(validationMessage, "error");
      return;
    }

    setIsBusy(true);
    try {
      await authApi.register(registerForm);
      showStatus("Регистрация выполнена. Теперь можно войти в систему.", "success");
      setRegisterForm(initialRegister);
      setAuthMode("login");
    } catch (error) {
      showStatus(error.message, "error");
    } finally {
      setIsBusy(false);
    }
  }

  async function handleActivateTariff(tariffId) {
    setIsBusy(true);
    try {
      await subscriptionApi.activateTariff(tariffId);
      await loadWorkspaceData();
      setActiveTab("subscriptions");
      showStatus(
        "Тариф активирован в режиме предоплаты. Создан счет на оплату.",
        "success",
      );
    } catch (error) {
      showStatus(error.message, "error");
    } finally {
      setIsBusy(false);
    }
  }

  async function handlePayInvoice(invoiceId) {
    setIsBusy(true);
    try {
      await invoiceApi.payInvoice(invoiceId);
      await loadWorkspaceData();
      showStatus("Счет оплачен, подписка переведена в активное состояние.", "success");
    } catch (error) {
      showStatus(error.message, "error");
    } finally {
      setIsBusy(false);
    }
  }

  async function handleExport(format) {
    setIsBusy(true);
    try {
      const file = await exportInvoices(format);
      downloadBlob(file);
      showStatus(`Экспорт ${format.toUpperCase()} подготовлен и скачан.`, "success");
    } catch (error) {
      showStatus(error.message, "error");
    } finally {
      setIsBusy(false);
    }
  }

  async function handleLogout() {
    setIsBusy(true);
    try {
      await authApi.logout();
      setUser(null);
      setSubscriptions([]);
      setInvoices([]);
      setTariffs([]);
      setOperatorInvoices([]);
      setOperatorSubscriptions([]);
      showStatus("Сеанс завершен.", "info");
    } finally {
      setIsBusy(false);
    }
  }

  async function handleOperatorLookup(event) {
    event.preventDefault();
    if (!operatorUserId.trim()) {
      showStatus("Укажите ID пользователя для операторского просмотра.", "error");
      return;
    }

    setIsBusy(true);
    try {
      const [subs, invs] = await Promise.all([
        subscriptionApi.getSubscriptionsByUser(operatorUserId.trim()),
        invoiceApi.getInvoicesByUser(operatorUserId.trim()),
      ]);
      setOperatorSubscriptions(subs);
      setOperatorInvoices(invs);
      showStatus("Операторские данные загружены.", "success");
    } catch (error) {
      showStatus(error.message, "error");
    } finally {
      setIsBusy(false);
    }
  }

  if (!user) {
    return (
      <main className="shell auth-shell">
        <section className="auth-hero">
          <div className="eyebrow">Secure SDLC + OWASP Top 10</div>
          <h1>Telecom Secure MVP</h1>
          <p>
            Интерфейс для защищенного MVP телеком-платформы: регистрация,
            аутентификация, активация тарифов, биллинг и аудит критичных действий.
          </p>

          <div className="hero-grid">
            <StatCard
              label="Роли"
              value="3"
              hint="customer, operator, admin"
            />
            <StatCard
              label="API"
              value="10+"
              hint="Авторизация, подписки, биллинг, export"
            />
            <StatCard
              label="Контроли"
              value="OWASP"
              hint="Валидация, RBAC, логирование, rotation"
            />
          </div>
        </section>

        <section className="auth-card">
          <div className="auth-tabs">
            <button
              className={authMode === "login" ? "active" : ""}
              onClick={() => setAuthMode("login")}
              type="button"
            >
              Вход
            </button>
            <button
              className={authMode === "register" ? "active" : ""}
              onClick={() => setAuthMode("register")}
              type="button"
            >
              Регистрация
            </button>
          </div>

          {authMode === "login" ? (
            <form className="form-grid" onSubmit={handleLogin}>
              <label>
                Имя пользователя
                <input
                  value={loginForm.username}
                  onChange={(event) =>
                    setLoginForm((prev) => ({
                      ...prev,
                      username: event.target.value,
                    }))
                  }
                  placeholder="testuser"
                />
              </label>
              <label>
                Пароль
                <input
                  type="password"
                  value={loginForm.password}
                  onChange={(event) =>
                    setLoginForm((prev) => ({
                      ...prev,
                      password: event.target.value,
                    }))
                  }
                  placeholder="Введите пароль"
                />
              </label>
              <button className="primary-button" disabled={isBusy} type="submit">
                {isBusy ? "Проверка..." : "Войти"}
              </button>
            </form>
          ) : (
            <form className="form-grid" onSubmit={handleRegister}>
              <label>
                Имя пользователя
                <input
                  value={registerForm.username}
                  onChange={(event) =>
                    setRegisterForm((prev) => ({
                      ...prev,
                      username: event.target.value,
                    }))
                  }
                  placeholder="newuser"
                />
              </label>
              <label>
                Email
                <input
                  type="email"
                  value={registerForm.email}
                  onChange={(event) =>
                    setRegisterForm((prev) => ({
                      ...prev,
                      email: event.target.value,
                    }))
                  }
                  placeholder="user@example.com"
                />
              </label>
              <label>
                Телефон
                <input
                  value={registerForm.phone}
                  onChange={(event) =>
                    setRegisterForm((prev) => ({
                      ...prev,
                      phone: event.target.value,
                    }))
                  }
                  placeholder="+7 (777) 123-45-67"
                />
              </label>
              <label>
                Пароль
                <input
                  type="password"
                  value={registerForm.password}
                  onChange={(event) =>
                    setRegisterForm((prev) => ({
                      ...prev,
                      password: event.target.value,
                    }))
                  }
                  placeholder="С буквой, цифрой и спецсимволом"
                />
              </label>
              <button className="primary-button" disabled={isBusy} type="submit">
                {isBusy ? "Создание..." : "Создать аккаунт"}
              </button>
            </form>
          )}

          {statusMessage ? (
            <div className={`status-banner ${statusType}`}>{statusMessage}</div>
          ) : null}
        </section>
      </main>
    );
  }

  return (
    <main className="shell app-shell">
      <header className="topbar">
        <div>
          <div className="eyebrow">Telecom Secure MVP</div>
          <h1>Кабинет абонента и оператора</h1>
        </div>
        <div className="topbar-actions">
          <div className="user-badge">
            <span>{user.username}</span>
            <strong>{user.role}</strong>
          </div>
          <button className="ghost-button" onClick={handleLogout} type="button">
            Выйти
          </button>
        </div>
      </header>

      <section className="hero-panel">
        <div className="hero-copy">
          <h2>Основной бизнес-сценарий собран в одном интерфейсе</h2>
          <p>
            Пользователь проходит безопасную аутентификацию, выбирает тариф,
            получает счет, оплачивает его и активирует подписку. Оператор и
            администратор могут просматривать клиентские данные в пределах своих прав.
          </p>
        </div>
        <div className="hero-grid">
          <StatCard
            label="Подписок"
            value={metrics.activeSubscriptions}
            hint="Активные и ожидающие оплаты"
          />
          <StatCard
            label="Неоплачено"
            value={metrics.unpaidInvoices}
            hint="Счета, требующие внимания"
          />
          <StatCard
            label="Сумма"
            value={formatMoney(metrics.totalDue)}
            hint="Текущая задолженность"
          />
        </div>
      </section>

      <nav className="app-nav">
        {displayedNav.map((item) => (
          <button
            key={item.id}
            className={activeTab === item.id ? "active" : ""}
            onClick={() => setActiveTab(item.id)}
            type="button"
          >
            {item.label}
          </button>
        ))}
      </nav>

      {statusMessage ? (
        <div className={`status-banner ${statusType}`}>{statusMessage}</div>
      ) : null}

      {activeTab === "overview" ? (
        <section className="panel-grid two-columns">
          <article className="panel-card accent-card">
            <h3>Состояние аккаунта</h3>
            <p>
              Аккаунт создан {formatDate(user.created_at)}. Текущая роль{" "}
              <strong>{user.role}</strong>, статус{" "}
              <strong>{user.is_active ? "active" : "inactive"}</strong>.
            </p>
            <ul className="feature-list">
              <li>JWT access и refresh token rotation</li>
              <li>RBAC для customer, operator, admin</li>
              <li>Валидация username, email, phone, password</li>
            </ul>
          </article>

          <article className="panel-card">
            <h3>Следующие шаги</h3>
            <p>
              Если подписка еще не оформлена, перейдите в раздел тарифов. Если
              счет уже выпущен, оплатите его в биллинге для активации услуги.
            </p>
            <div className="quick-actions">
              <button
                className="primary-button"
                onClick={() => setActiveTab("tariffs")}
                type="button"
              >
                Выбрать тариф
              </button>
              <button
                className="secondary-button"
                onClick={() => setActiveTab("billing")}
                type="button"
              >
                Перейти к счетам
              </button>
            </div>
          </article>
        </section>
      ) : null}

      {activeTab === "tariffs" ? (
        <section className="card-grid">
          {tariffs.length ? (
            tariffs.map((tariff) => (
              <article className="tariff-card" key={tariff.id}>
                <div className="tariff-head">
                  <span className="tariff-chip">Тариф #{tariff.id}</span>
                  <strong>{formatMoney(tariff.monthly_price)}</strong>
                </div>
                <h3>{tariff.name}</h3>
                <p>{tariff.description || "Оптимизированный пакет услуг для связи."}</p>
                <div className="tariff-metrics">
                  <span>{tariff.data_limit_gb} ГБ</span>
                  <span>{tariff.minutes_limit} мин</span>
                  <span>{tariff.sms_limit} SMS</span>
                </div>
                <button
                  className="primary-button"
                  disabled={isBusy}
                  onClick={() => handleActivateTariff(tariff.id)}
                  type="button"
                >
                  Активировать
                </button>
              </article>
            ))
          ) : (
            <EmptyState
              title="Нет доступных тарифов"
              text="Backend не вернул активные тарифные планы."
            />
          )}
        </section>
      ) : null}

      {activeTab === "subscriptions" ? (
        <section className="card-grid">
          {subscriptions.length ? (
            subscriptions.map((subscription) => (
              <article className="panel-card subscription-card" key={subscription.id}>
                <div className="card-meta">
                  <span className={`status-pill ${subscription.status}`}>
                    {subscription.status}
                  </span>
                  <span>ID #{subscription.id}</span>
                </div>
                <h3>{subscription.tariff_plan?.name || "Тариф"}</h3>
                <p>
                  Следующее списание: {formatDate(subscription.next_billing_date)}
                </p>
                <ul className="feature-list">
                  <li>Статус активности: {subscription.is_active ? "да" : "нет"}</li>
                  <li>Трафик: {subscription.tariff_plan?.data_limit_gb ?? "-"} ГБ</li>
                  <li>Минуты: {subscription.tariff_plan?.minutes_limit ?? "-"}</li>
                </ul>
              </article>
            ))
          ) : (
            <EmptyState
              title="Подписок пока нет"
              text="Активируйте тариф, чтобы backend создал подписку и счет."
            />
          )}
        </section>
      ) : null}

      {activeTab === "billing" ? (
        <section className="panel-stack">
          <article className="panel-card">
            <div className="section-heading">
              <div>
                <h3>Счета и экспорт</h3>
                <p>Можно оплатить pending-счет или выгрузить данные в CSV/JSON.</p>
              </div>
              <div className="quick-actions">
                <button
                  className="secondary-button"
                  disabled={isBusy}
                  onClick={() => handleExport("csv")}
                  type="button"
                >
                  Экспорт CSV
                </button>
                <button
                  className="secondary-button"
                  disabled={isBusy}
                  onClick={() => handleExport("json")}
                  type="button"
                >
                  Экспорт JSON
                </button>
              </div>
            </div>
          </article>

          <section className="card-grid">
            {invoices.length ? (
              invoices.map((invoice) => (
                <article className="panel-card invoice-card" key={invoice.id}>
                  <div className="card-meta">
                    <span className={`status-pill ${getInvoiceTone(invoice.status)}`}>
                      {invoice.status}
                    </span>
                    <span>Счет #{invoice.id}</span>
                  </div>
                  <h3>{formatMoney(invoice.amount)}</h3>
                  <p>Оплатить до {formatDate(invoice.due_date)}</p>
                  <ul className="feature-list">
                    <li>Подписка: #{invoice.subscription_id}</li>
                    <li>Период: {formatDate(invoice.billing_period_start)}</li>
                    <li>Создан: {formatDate(invoice.created_at)}</li>
                  </ul>
                  <button
                    className="primary-button"
                    disabled={isBusy || invoice.status !== "pending"}
                    onClick={() => handlePayInvoice(invoice.id)}
                    type="button"
                  >
                    {invoice.status === "paid" ? "Уже оплачен" : "Оплатить счет"}
                  </button>
                </article>
              ))
            ) : (
              <EmptyState
                title="Счета не найдены"
                text="После активации тарифа backend сформирует prepaid-счет."
              />
            )}
          </section>
        </section>
      ) : null}

      {activeTab === "security" ? (
        <section className="panel-grid two-columns">
          <article className="panel-card">
            <h3>Реализованные механизмы защиты</h3>
            <ul className="feature-list">
              <li>Хеширование паролей через bcrypt/passlib</li>
              <li>Ограничение размера запросов middleware</li>
              <li>Проверка токенов и ротация refresh token</li>
              <li>Логирование входа, отказов, оплаты и попыток несанкционированного доступа</li>
              <li>Разграничение доступа по ролям и владельцу ресурса</li>
            </ul>
          </article>

          <article className="panel-card">
            <h3>OWASP Top 10 Coverage</h3>
            <ul className="feature-list">
              <li>Broken Access Control: защищены invoice/subscription endpoint’ы</li>
              <li>Authentication Failures: lockout после серии неудачных входов</li>
              <li>Injection: ORM и валидация входных данных</li>
              <li>Security Logging: аудит безопасности без утечки секретов</li>
              <li>Mishandling of Exceptional Conditions: безопасные 4xx/5xx ответы</li>
            </ul>
          </article>
        </section>
      ) : null}

      {activeTab === "operator" ? (
        <section className="panel-stack">
          <article className="panel-card">
            <h3>Операторский доступ</h3>
            <p>
              Раздел доступен только ролям <strong>operator</strong> и{" "}
              <strong>admin</strong>. Введите ID пользователя, чтобы получить
              его подписки и счета через защищенные backend-endpoint’ы.
            </p>
            <form className="operator-form" onSubmit={handleOperatorLookup}>
              <input
                value={operatorUserId}
                onChange={(event) => setOperatorUserId(event.target.value)}
                placeholder="Например: 1"
              />
              <button className="primary-button" disabled={isBusy} type="submit">
                Загрузить данные
              </button>
            </form>
          </article>

          <section className="panel-grid two-columns">
            <article className="panel-card">
              <h3>Подписки пользователя</h3>
              {operatorSubscriptions.length ? (
                <ul className="data-list">
                  {operatorSubscriptions.map((item) => (
                    <li key={item.id}>
                      #{item.id} · {item.tariff_plan?.name || "Тариф"} · {item.status}
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="muted-text">Данные еще не запрошены.</p>
              )}
            </article>

            <article className="panel-card">
              <h3>Счета пользователя</h3>
              {operatorInvoices.length ? (
                <ul className="data-list">
                  {operatorInvoices.map((item) => (
                    <li key={item.id}>
                      #{item.id} · {formatMoney(item.amount)} · {item.status}
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="muted-text">Данные еще не запрошены.</p>
              )}
            </article>
          </section>
        </section>
      ) : null}
    </main>
  );
}
