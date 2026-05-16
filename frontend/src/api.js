const ACCESS_TOKEN_KEY = "telecom.accessToken";
const REFRESH_TOKEN_KEY = "telecom.refreshToken";
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "";

export function loadTokens() {
  return {
    accessToken: sessionStorage.getItem(ACCESS_TOKEN_KEY),
    refreshToken: sessionStorage.getItem(REFRESH_TOKEN_KEY),
  };
}

export function saveTokens(tokens) {
  sessionStorage.setItem(ACCESS_TOKEN_KEY, tokens.access_token);
  sessionStorage.setItem(REFRESH_TOKEN_KEY, tokens.refresh_token);
}

export function clearTokens() {
  sessionStorage.removeItem(ACCESS_TOKEN_KEY);
  sessionStorage.removeItem(REFRESH_TOKEN_KEY);
}

async function parseResponse(response) {
  const contentType = response.headers.get("content-type") || "";

  if (contentType.includes("application/json")) {
    return response.json();
  }

  return response.text();
}

async function refreshAccessToken() {
  const { refreshToken } = loadTokens();
  if (!refreshToken) {
    throw new Error("Сессия истекла. Выполните вход заново.");
  }

  const response = await fetch(`${API_BASE_URL}/api/auth/refresh`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ refresh_token: refreshToken }),
  });

  const payload = await parseResponse(response);
  if (!response.ok) {
    clearTokens();
    throw new Error(payload.error || "Не удалось обновить сессию");
  }

  saveTokens(payload);
  return payload.access_token;
}

export async function apiRequest(path, options = {}, allowRefresh = true) {
  const { accessToken } = loadTokens();
  const headers = new Headers(options.headers || {});

  if (
    !headers.has("Content-Type") &&
    options.body &&
    !(options.body instanceof FormData)
  ) {
    headers.set("Content-Type", "application/json");
  }

  if (accessToken) {
    headers.set("Authorization", `Bearer ${accessToken}`);
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
  });

  if (response.status === 401 && allowRefresh && loadTokens().refreshToken) {
    try {
      const newAccessToken = await refreshAccessToken();
      headers.set("Authorization", `Bearer ${newAccessToken}`);
      const retry = await fetch(`${API_BASE_URL}${path}`, { ...options, headers });
      const retryPayload = await parseResponse(retry);
      if (!retry.ok) {
        throw new Error(retryPayload.error || "Запрос не выполнен");
      }
      return retryPayload;
    } catch (error) {
      clearTokens();
      throw error;
    }
  }

  const payload = await parseResponse(response);
  if (!response.ok) {
    throw new Error(payload.error || "Запрос не выполнен");
  }

  return payload;
}

export async function exportInvoices(format) {
  const { accessToken } = loadTokens();
  const response = await fetch(
    `${API_BASE_URL}/api/billing/invoices/export?format=${format}`,
    {
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
    },
  );

  if (response.status === 401) {
    await refreshAccessToken();
    return exportInvoices(format);
  }

  if (!response.ok) {
    const payload = await parseResponse(response);
    throw new Error(payload.error || "Не удалось экспортировать данные");
  }

  const blob = await response.blob();
  const disposition = response.headers.get("Content-Disposition") || "";
  const filenameMatch = disposition.match(/filename="(.+)"/);
  const filename = filenameMatch?.[1] || `invoices.${format}`;

  return { blob, filename };
}

export const authApi = {
  register: (payload) =>
    apiRequest("/api/auth/register", {
      method: "POST",
      body: JSON.stringify(payload),
    }, false),
  login: async (payload) => {
    const tokens = await apiRequest(
      "/api/auth/login",
      {
        method: "POST",
        body: JSON.stringify(payload),
      },
      false,
    );
    saveTokens(tokens);
    return tokens;
  },
  me: () => apiRequest("/api/auth/me"),
  logout: async () => {
    try {
      await apiRequest("/api/auth/logout", { method: "POST" });
    } finally {
      clearTokens();
    }
  },
};

export const subscriptionApi = {
  getTariffs: () => apiRequest("/api/subscriptions/tariffs"),
  getSubscriptions: () => apiRequest("/api/subscriptions"),
  getSubscription: (subscriptionId) =>
    apiRequest(`/api/subscriptions/${subscriptionId}`),
  activateTariff: (tariffId) =>
    apiRequest("/api/subscriptions/activate", {
      method: "POST",
      body: JSON.stringify({ tariff_id: tariffId }),
    }),
  getSubscriptionsByUser: (userId) =>
    apiRequest(`/api/subscriptions/user/${userId}`),
};

export const invoiceApi = {
  getInvoices: () => apiRequest("/api/billing/invoices"),
  getInvoice: (invoiceId) => apiRequest(`/api/billing/invoices/${invoiceId}`),
  getInvoiceStatus: (invoiceId) =>
    apiRequest(`/api/billing/invoices/${invoiceId}/status`),
  payInvoice: (invoiceId) =>
    apiRequest(`/api/billing/invoices/${invoiceId}/pay`, {
      method: "POST",
    }),
  getInvoicesByUser: (userId) =>
    apiRequest(`/api/billing/invoices/user/${userId}`),
};

export const publicApi = {
  getRoot: async () => {
    const response = await fetch(`${API_BASE_URL}/`);
    const payload = await parseResponse(response);
    if (!response.ok) {
      throw new Error(payload.error || "Не удалось загрузить сведения о сервисе");
    }
    return payload;
  },
  getHealth: async () => {
    const response = await fetch(`${API_BASE_URL}/health`);
    const payload = await parseResponse(response);
    if (!response.ok) {
      throw new Error(payload.error || "Не удалось проверить состояние сервиса");
    }
    return payload;
  },
};
