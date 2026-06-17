/**
 * hooks/useAdminData.js — Nubo Express
 *
 * Custom Hook centralizado para todas las peticiones al backend Admin + Contabilidad.
 * Gestiona de forma limpia:
 *   - Estados de carga (loading), error y datos
 *   - Autenticación via JWT (Bearer token)
 *   - Cancelación de peticiones al desmontar el componente (AbortController)
 *   - Caché en memoria por TTL configurable
 *   - Reintentos automáticos con backoff exponencial
 *   - Paginación de recursos listables
 *   - Exportación de archivos (CSV / JSON)
 *
 * Uso básico:
 *   const { dashboard, fetchDashboard } = useAdminData()
 *   useEffect(() => { fetchDashboard() }, [])
 */

import { useState, useCallback, useRef, useEffect } from "react";

// ─────────────────────────────────────────────────────────────────
//  CONFIGURACIÓN GLOBAL
// ─────────────────────────────────────────────────────────────────

const API_BASE_URL = import.meta.env?.VITE_API_URL ?? "http://localhost:8000";

/** TTL de caché en milisegundos para endpoints de solo lectura */
const CACHE_TTL_MS = 30_000; // 30 segundos

/** Número máximo de reintentos ante errores de red */
const MAX_RETRIES = 2;

/** Delay base para backoff exponencial (ms) */
const RETRY_BASE_DELAY_MS = 500;


// ─────────────────────────────────────────────────────────────────
//  CACHÉ EN MEMORIA (singleton por módulo)
// ─────────────────────────────────────────────────────────────────

/** @type {Map<string, { data: any, expiresAt: number }>} */
const _cache = new Map();

const cache = {
  get(key) {
    const entry = _cache.get(key);
    if (!entry) return null;
    if (Date.now() > entry.expiresAt) {
      _cache.delete(key);
      return null;
    }
    return entry.data;
  },
  set(key, data, ttl = CACHE_TTL_MS) {
    _cache.set(key, { data, expiresAt: Date.now() + ttl });
  },
  invalidate(prefix) {
    for (const key of _cache.keys()) {
      if (key.startsWith(prefix)) _cache.delete(key);
    }
  },
  clear() {
    _cache.clear();
  },
};


// ─────────────────────────────────────────────────────────────────
//  CLIENTE HTTP BASE
// ─────────────────────────────────────────────────────────────────

/**
 * Recupera el JWT del almacenamiento local.
 * Adapta esta función a tu sistema de auth (Context, Zustand, Cookie, etc.)
 */
function getAuthToken() {
  return localStorage.getItem("nubo_access_token") ?? "";
}

/**
 * Construye los headers comunes para todas las peticiones.
 */
function buildHeaders(extra = {}) {
  const token = getAuthToken();
  return {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...extra,
  };
}

/**
 * Núcleo del cliente HTTP con:
 *   - Soporte de AbortSignal para cancelación
 *   - Reintentos automáticos con backoff exponencial
 *   - Normalización de errores
 *
 * @param {string} path           - Ruta relativa al API_BASE_URL
 * @param {RequestInit} options   - Opciones nativas de fetch
 * @param {number} retries        - Intentos restantes
 * @returns {Promise<any>}        - JSON parseado o Blob (para descargas)
 */
async function apiFetch(path, options = {}, retries = MAX_RETRIES) {
  const url = `${API_BASE_URL}${path}`;

  const response = await fetch(url, {
    ...options,
    headers: buildHeaders(options.headers ?? {}),
  });

  // Errores HTTP sin reintentar (cliente)
  if (response.status === 401) {
    throw new ApiError("Sesión expirada. Por favor, inicia sesión de nuevo.", 401);
  }
  if (response.status === 403) {
    throw new ApiError("No tienes permisos para realizar esta acción.", 403);
  }
  if (response.status === 404) {
    const body = await response.json().catch(() => ({}));
    throw new ApiError(body.detail ?? "Recurso no encontrado.", 404);
  }
  if (response.status === 422) {
    const body = await response.json().catch(() => ({}));
    throw new ApiError(
      body.detail?.[0]?.msg ?? "Datos de entrada inválidos.",
      422
    );
  }

  // Errores de servidor — reintentar con backoff
  if (!response.ok) {
    if (retries > 0) {
      const delay = RETRY_BASE_DELAY_MS * (MAX_RETRIES - retries + 1);
      await sleep(delay);
      return apiFetch(path, options, retries - 1);
    }
    const body = await response.json().catch(() => ({}));
    throw new ApiError(
      body.detail ?? `Error del servidor (${response.status}).`,
      response.status
    );
  }

  // Descargas binarias
  const contentType = response.headers.get("content-type") ?? "";
  if (
    contentType.includes("text/csv") ||
    contentType.includes("application/octet-stream")
  ) {
    return response.blob();
  }

  return response.json();
}

/** Error tipado con código HTTP para manejo diferenciado en la UI */
class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.name  = "ApiError";
    this.status = status;
  }
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * Serializa un objeto de filtros a query string.
 * Ignora valores null, undefined y strings vacíos.
 */
function toQueryString(params = {}) {
  const qs = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v !== null && v !== undefined && v !== "") {
      qs.set(k, String(v));
    }
  });
  const str = qs.toString();
  return str ? `?${str}` : "";
}

/**
 * Dispara la descarga de un Blob como archivo en el navegador.
 */
function triggerDownload(blob, filename) {
  const url = URL.createObjectURL(blob);
  const a   = document.createElement("a");
  a.href     = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}


// ─────────────────────────────────────────────────────────────────
//  ESTADO INICIAL
// ─────────────────────────────────────────────────────────────────

/** Estructura de estado por recurso: { data, loading, error } */
const makeSlice = (data = null) => ({ data, loading: false, error: null });

const INITIAL_STATE = {
  // ── Dashboard ──────────────────────────────────────────────────
  dashboard:    makeSlice(),

  // ── Mapa en vivo ───────────────────────────────────────────────
  liveMap:      makeSlice({ count: 0, couriers: [] }),

  // ── Usuarios ───────────────────────────────────────────────────
  users:        makeSlice({ total: 0, page: 1, per_page: 20, pages: 0, data: [] }),

  // ── Couriers ───────────────────────────────────────────────────
  couriers:     makeSlice({ total: 0, page: 1, per_page: 20, pages: 0, data: [] }),

  // ── Tarifas ────────────────────────────────────────────────────
  rates:        makeSlice([]),

  // ── Transacciones ──────────────────────────────────────────────
  transactions: makeSlice({ total: 0, page: 1, per_page: 30, pages: 0, data: [] }),
  txSummary:    makeSlice(),

  // ── Caja de efectivo ───────────────────────────────────────────
  cashBalance:  makeSlice(),

  // ── Stripe ─────────────────────────────────────────────────────
  stripeBalance: makeSlice(),
  stripeCharges: makeSlice({ charges: [], has_more: false }),

  // ── Nóminas ────────────────────────────────────────────────────
  payroll:        makeSlice({ total: 0, page: 1, per_page: 30, pages: 0, data: [] }),
  payrollSummary: makeSlice(),

  // ── Audit logs ─────────────────────────────────────────────────
  auditLogs:    makeSlice({ total: 0, page: 1, per_page: 50, pages: 0, data: [] }),

  // ── Operaciones de escritura ────────────────────────────────────
  mutation: { loading: false, error: null, success: false },
};


// ─────────────────────────────────────────────────────────────────
//  HOOK PRINCIPAL
// ─────────────────────────────────────────────────────────────────

/**
 * useAdminData — Hook centralizado para el panel de administración
 * de Nubo Express.
 *
 * @returns {object} Estado reactivo + funciones de acción
 */
export function useAdminData() {
  const [state, setState] = useState(INITIAL_STATE);

  /**
   * Ref de AbortControllers activos.
   * Al desmontar el componente, se cancelan todas las peticiones en vuelo.
   */
  const abortControllersRef = useRef(new Map());

  // Cancelar todas las peticiones al desmontar
  useEffect(() => {
    return () => {
      abortControllersRef.current.forEach((ctrl) => ctrl.abort());
      abortControllersRef.current.clear();
    };
  }, []);


  // ──────────────────────────────────────────────────────────────
  //  HELPERS DE ESTADO
  // ──────────────────────────────────────────────────────────────

  /** Marca un slice como en carga */
  const setLoading = useCallback((slice) => {
    setState((prev) => ({
      ...prev,
      [slice]: { ...prev[slice], loading: true, error: null },
    }));
  }, []);

  /** Actualiza un slice con los datos recibidos */
  const setData = useCallback((slice, data) => {
    setState((prev) => ({
      ...prev,
      [slice]: { data, loading: false, error: null },
    }));
  }, []);

  /** Marca un slice con error */
  const setError = useCallback((slice, error) => {
    setState((prev) => ({
      ...prev,
      [slice]: { ...prev[slice], loading: false, error: error.message ?? String(error) },
    }));
  }, []);

  /** Estado de mutation (operaciones de escritura) */
  const setMutation = useCallback((patch) => {
    setState((prev) => ({ ...prev, mutation: { ...prev.mutation, ...patch } }));
  }, []);

  const resetMutation = useCallback(() => {
    setState((prev) => ({
      ...prev,
      mutation: { loading: false, error: null, success: false },
    }));
  }, []);


  // ──────────────────────────────────────────────────────────────
  //  EJECUTOR GENÉRICO
  // ──────────────────────────────────────────────────────────────

  /**
   * Ejecuta una petición GET con caché y AbortController.
   *
   * @param {string}   slice       - Clave del estado a actualizar
   * @param {string}   path        - Ruta del endpoint
   * @param {boolean}  useCache    - ¿Usar caché en memoria?
   */
  const fetchSlice = useCallback(
    async (slice, path, useCache = true) => {
      // Cancelar petición anterior del mismo slice
      const prevCtrl = abortControllersRef.current.get(slice);
      if (prevCtrl) prevCtrl.abort();

      const ctrl = new AbortController();
      abortControllersRef.current.set(slice, ctrl);

      // Revisar caché antes de ir al servidor
      if (useCache) {
        const cached = cache.get(path);
        if (cached) {
          setData(slice, cached);
          return cached;
        }
      }

      setLoading(slice);
      try {
        const data = await apiFetch(path, { signal: ctrl.signal });
        setData(slice, data);
        if (useCache) cache.set(path, data);
        return data;
      } catch (err) {
        if (err.name === "AbortError") return; // Cancelación silenciosa
        setError(slice, err);
        throw err;
      } finally {
        abortControllersRef.current.delete(slice);
      }
    },
    [setData, setLoading, setError]
  );

  /**
   * Ejecuta una petición de escritura (POST / PUT / DELETE).
   * Invalida caché de los prefijos indicados al terminar con éxito.
   *
   * @param {string}   method           - HTTP method
   * @param {string}   path             - Ruta del endpoint
   * @param {any}      body             - Cuerpo JSON (opcional)
   * @param {string[]} invalidatePaths  - Prefijos de caché a invalidar
   */
  const mutate = useCallback(
    async (method, path, body = null, invalidatePaths = []) => {
      setMutation({ loading: true, error: null, success: false });
      try {
        const data = await apiFetch(path, {
          method,
          ...(body ? { body: JSON.stringify(body) } : {}),
        });
        setMutation({ loading: false, error: null, success: true });
        invalidatePaths.forEach((p) => cache.invalidate(p));
        return data;
      } catch (err) {
        setMutation({ loading: false, error: err.message ?? String(err), success: false });
        throw err;
      }
    },
    [setMutation]
  );


  // ─────────────────────────────────────────────────────────────
  //  1. DASHBOARD
  // ─────────────────────────────────────────────────────────────

  const fetchDashboard = useCallback(() => {
    return fetchSlice("dashboard", "/admin/dashboard", false); // Sin caché: datos en tiempo real
  }, [fetchSlice]);


  // ─────────────────────────────────────────────────────────────
  //  2. MAPA EN VIVO
  // ─────────────────────────────────────────────────────────────

  /**
   * Obtiene posiciones GPS de couriers activos.
   * @param {string} [zone] - Filtrar por zona (opcional)
   */
  const fetchLiveMap = useCallback(
    (zone = null) => {
      const qs = toQueryString({ zone });
      return fetchSlice("liveMap", `/admin/map/live${qs}`, false);
    },
    [fetchSlice]
  );


  // ─────────────────────────────────────────────────────────────
  //  3. USUARIOS
  // ─────────────────────────────────────────────────────────────

  /**
   * @param {{ page?, per_page?, role?, is_active?, search? }} filters
   */
  const fetchUsers = useCallback(
    (filters = {}) => {
      const qs = toQueryString({ page: 1, per_page: 20, ...filters });
      return fetchSlice("users", `/admin/users${qs}`);
    },
    [fetchSlice]
  );

  /**
   * Crea un nuevo usuario.
   * @param {{ email, full_name, role, password }} payload
   */
  const createUser = useCallback(
    (payload) =>
      mutate("POST", "/admin/users", payload, ["/admin/users"]),
    [mutate]
  );

  /**
   * Activa / desactiva un usuario.
   * @param {string} userId
   */
  const toggleUserStatus = useCallback(
    (userId) =>
      mutate("PUT", `/admin/users/${userId}/status`, null, ["/admin/users"]),
    [mutate]
  );

  /**
   * Actualiza los permisos granulares de un usuario.
   * @param {string} userId
   * @param {object} permissions
   */
  const updateUserPermissions = useCallback(
    (userId, permissions) =>
      mutate(
        "PUT",
        `/admin/users/${userId}/permissions`,
        permissions,
        ["/admin/users"]
      ),
    [mutate]
  );


  // ─────────────────────────────────────────────────────────────
  //  4. COURIERS
  // ─────────────────────────────────────────────────────────────

  /**
   * @param {{ page?, per_page?, status?, zone? }} filters
   */
  const fetchCouriers = useCallback(
    (filters = {}) => {
      const qs = toQueryString({ page: 1, per_page: 20, ...filters });
      return fetchSlice("couriers", `/admin/couriers${qs}`);
    },
    [fetchSlice]
  );

  const createCourier = useCallback(
    (payload) =>
      mutate("POST", "/admin/couriers", payload, ["/admin/couriers"]),
    [mutate]
  );

  const updateCourier = useCallback(
    (courierId, payload) =>
      mutate("PUT", `/admin/couriers/${courierId}`, payload, ["/admin/couriers"]),
    [mutate]
  );


  // ─────────────────────────────────────────────────────────────
  //  5. TARIFAS
  // ─────────────────────────────────────────────────────────────

  const fetchRates = useCallback(
    (onlyActive = true) =>
      fetchSlice("rates", `/admin/rates${toQueryString({ only_active: onlyActive })}`),
    [fetchSlice]
  );

  const updateRate = useCallback(
    (rateId, payload) =>
      mutate("PUT", `/admin/rates/${rateId}`, payload, ["/admin/rates"]),
    [mutate]
  );


  // ─────────────────────────────────────────────────────────────
  //  6. TRANSACCIONES
  // ─────────────────────────────────────────────────────────────

  /**
   * @param {{
   *   page?, per_page?, type?, currency?, payment_method?,
   *   courier_id?, date_from?, date_to?, is_reconciled?
   * }} filters
   */
  const fetchTransactions = useCallback(
    (filters = {}) => {
      const qs = toQueryString({ page: 1, per_page: 30, ...filters });
      return fetchSlice("transactions", `/accounting/transactions${qs}`);
    },
    [fetchSlice]
  );

  const fetchTransactionSummary = useCallback(
    (filters = {}) => {
      const qs = toQueryString(filters);
      return fetchSlice("txSummary", `/accounting/transactions/summary${qs}`, false);
    },
    [fetchSlice]
  );

  const createTransaction = useCallback(
    (payload) =>
      mutate("POST", "/accounting/transactions", payload, [
        "/accounting/transactions",
        "/accounting/cash",
      ]),
    [mutate]
  );


  // ─────────────────────────────────────────────────────────────
  //  7. CAJA DE EFECTIVO
  // ─────────────────────────────────────────────────────────────

  const fetchCashBalance = useCallback(
    () => fetchSlice("cashBalance", "/accounting/cash/balance", false),
    [fetchSlice]
  );

  /**
   * @param {{ amount: number, currency: 'MAD'|'EUR', description: string }} payload
   */
  const cashIn = useCallback(
    ({ amount, currency, description }) => {
      const qs = toQueryString({ amount, currency, description });
      return mutate("POST", `/accounting/cash/in${qs}`, null, [
        "/accounting/cash",
        "/accounting/transactions",
      ]);
    },
    [mutate]
  );

  const cashOut = useCallback(
    ({ amount, currency, description }) => {
      const qs = toQueryString({ amount, currency, description });
      return mutate("POST", `/accounting/cash/out${qs}`, null, [
        "/accounting/cash",
        "/accounting/transactions",
      ]);
    },
    [mutate]
  );


  // ─────────────────────────────────────────────────────────────
  //  8. STRIPE
  // ─────────────────────────────────────────────────────────────

  const fetchStripeBalance = useCallback(
    () => fetchSlice("stripeBalance", "/accounting/stripe/balance", false),
    [fetchSlice]
  );

  const fetchStripeCharges = useCallback(
    (limit = 25, startingAfter = null) => {
      const qs = toQueryString({ limit, starting_after: startingAfter });
      return fetchSlice("stripeCharges", `/accounting/stripe/charges${qs}`, false);
    },
    [fetchSlice]
  );

  const createStripePayout = useCallback(
    ({ amount, description }) => {
      const qs = toQueryString({ amount, description });
      return mutate("POST", `/accounting/stripe/payout${qs}`, null, [
        "/accounting/stripe",
        "/accounting/transactions",
      ]);
    },
    [mutate]
  );


  // ─────────────────────────────────────────────────────────────
  //  9. NÓMINAS
  // ─────────────────────────────────────────────────────────────

  /**
   * @param {{ page?, per_page?, is_paid?, date_from?, date_to? }} filters
   */
  const fetchPayroll = useCallback(
    (filters = {}) => {
      const qs = toQueryString({ page: 1, per_page: 30, ...filters });
      return fetchSlice("payroll", `/accounting/payroll${qs}`);
    },
    [fetchSlice]
  );

  const fetchPayrollSummary = useCallback(
    () => fetchSlice("payrollSummary", "/accounting/payroll/summary", false),
    [fetchSlice]
  );

  /**
   * Genera las nóminas del período indicado.
   * @param {{ date_from: string, date_to: string }} period  — YYYY-MM-DD
   */
  const generatePayroll = useCallback(
    ({ date_from, date_to }) => {
      const qs = toQueryString({ date_from, date_to });
      return mutate("POST", `/accounting/payroll/generate${qs}`, null, [
        "/accounting/payroll",
        "/accounting/transactions",
      ]);
    },
    [mutate]
  );

  /**
   * Marca una entrada de nómina como pagada.
   * @param {string} entryId
   * @param {string} paymentMethod  — 'cash_mad' | 'cash_eur' | 'bank_transfer' | 'stripe'
   */
  const payPayrollEntry = useCallback(
    (entryId, paymentMethod) => {
      const qs = toQueryString({ payment_method: paymentMethod });
      return mutate(
        "PUT",
        `/accounting/payroll/${entryId}/pay${qs}`,
        null,
        ["/accounting/payroll", "/accounting/transactions"]
      );
    },
    [mutate]
  );


  // ─────────────────────────────────────────────────────────────
  //  10. AUDIT LOGS
  // ─────────────────────────────────────────────────────────────

  /**
   * @param {{ page?, per_page?, actor_id?, action?, resource? }} filters
   */
  const fetchAuditLogs = useCallback(
    (filters = {}) => {
      const qs = toQueryString({ page: 1, per_page: 50, ...filters });
      return fetchSlice("auditLogs", `/admin/audit-logs${qs}`);
    },
    [fetchSlice]
  );


  // ─────────────────────────────────────────────────────────────
  //  11. EXPORTACIÓN
  // ─────────────────────────────────────────────────────────────

  /**
   * Descarga transacciones como CSV o JSON.
   * @param {{ format?: 'csv'|'json', date_from?, date_to?, type?, currency? }} params
   */
  const exportTransactions = useCallback(async (params = {}) => {
    const { format = "csv", ...filters } = params;
    const qs = toQueryString({ format, ...filters });

    setMutation({ loading: true, error: null, success: false });
    try {
      const blob = await apiFetch(`/accounting/export/transactions${qs}`);
      const ext  = format === "json" ? "json" : "csv";
      triggerDownload(blob, `nubo_transactions_${Date.now()}.${ext}`);
      setMutation({ loading: false, error: null, success: true });
    } catch (err) {
      setMutation({ loading: false, error: err.message, success: false });
      throw err;
    }
  }, [setMutation]);

  /**
   * Descarga nóminas como CSV o JSON.
   * @param {{ format?: 'csv'|'json', is_paid?, date_from?, date_to? }} params
   */
  const exportPayroll = useCallback(async (params = {}) => {
    const { format = "csv", ...filters } = params;
    const qs = toQueryString({ format, ...filters });

    setMutation({ loading: true, error: null, success: false });
    try {
      const blob = await apiFetch(`/accounting/export/payroll${qs}`);
      const ext  = format === "json" ? "json" : "csv";
      triggerDownload(blob, `nubo_payroll_${Date.now()}.${ext}`);
      setMutation({ loading: false, error: null, success: true });
    } catch (err) {
      setMutation({ loading: false, error: err.message, success: false });
      throw err;
    }
  }, [setMutation]);

  /**
   * Descarga el reporte contable completo en JSON.
   * @param {{ date_from: string, date_to: string }} period
   */
  const exportFullReport = useCallback(async ({ date_from, date_to }) => {
    const qs = toQueryString({ date_from, date_to });

    setMutation({ loading: true, error: null, success: false });
    try {
      const blob = await apiFetch(`/accounting/export/report${qs}`);
      triggerDownload(blob, `nubo_report_${date_from}_${date_to}.json`);
      setMutation({ loading: false, error: null, success: true });
    } catch (err) {
      setMutation({ loading: false, error: err.message, success: false });
      throw err;
    }
  }, [setMutation]);


  // ─────────────────────────────────────────────────────────────
  //  RETORNO DEL HOOK
  // ─────────────────────────────────────────────────────────────

  return {
    // ── Estado (solo lectura) ──────────────────────────────────
    ...state,

    // ── Utilitarios de estado ──────────────────────────────────
    resetMutation,

    // ── Dashboard ─────────────────────────────────────────────
    fetchDashboard,

    // ── Mapa en vivo ──────────────────────────────────────────
    fetchLiveMap,

    // ── Usuarios ──────────────────────────────────────────────
    fetchUsers,
    createUser,
    toggleUserStatus,
    updateUserPermissions,

    // ── Couriers ──────────────────────────────────────────────
    fetchCouriers,
    createCourier,
    updateCourier,

    // ── Tarifas ───────────────────────────────────────────────
    fetchRates,
    updateRate,

    // ── Transacciones ─────────────────────────────────────────
    fetchTransactions,
    fetchTransactionSummary,
    createTransaction,

    // ── Caja de efectivo ──────────────────────────────────────
    fetchCashBalance,
    cashIn,
    cashOut,

    // ── Stripe ────────────────────────────────────────────────
    fetchStripeBalance,
    fetchStripeCharges,
    createStripePayout,

    // ── Nóminas ───────────────────────────────────────────────
    fetchPayroll,
    fetchPayrollSummary,
    generatePayroll,
    payPayrollEntry,

    // ── Audit logs ────────────────────────────────────────────
    fetchAuditLogs,

    // ── Exportación ───────────────────────────────────────────
    exportTransactions,
    exportPayroll,
    exportFullReport,
  };
}


// ─────────────────────────────────────────────────────────────────
//  HOOKS DERIVADOS (granulares por módulo)
// ─────────────────────────────────────────────────────────────────

/**
 * Hook mínimo solo para el dashboard.
 * Útil en componentes que solo necesitan las métricas principales.
 *
 * @param {number} [pollingMs=0]  - Intervalo de polling en ms (0 = sin polling)
 *
 * @example
 *   const { data, loading, error, refresh } = useDashboard(15000)
 */
export function useDashboard(pollingMs = 0) {
  const { dashboard, fetchDashboard } = useAdminData();

  useEffect(() => {
    fetchDashboard();
    if (!pollingMs) return;
    const id = setInterval(fetchDashboard, pollingMs);
    return () => clearInterval(id);
  }, [pollingMs]); // eslint-disable-line react-hooks/exhaustive-deps

  return {
    data:    dashboard.data,
    loading: dashboard.loading,
    error:   dashboard.error,
    refresh: fetchDashboard,
  };
}

/**
 * Hook mínimo para el mapa en vivo con polling automático.
 *
 * @param {number} [pollingMs=20000]  - Intervalo de refresco (default: 20 s)
 * @param {string} [zone]             - Filtrar por zona
 *
 * @example
 *   const { couriers, loading } = useLiveMap(15000, "Centro")
 */
export function useLiveMap(pollingMs = 20_000, zone = null) {
  const { liveMap, fetchLiveMap } = useAdminData();

  useEffect(() => {
    fetchLiveMap(zone);
    const id = setInterval(() => fetchLiveMap(zone), pollingMs);
    return () => clearInterval(id);
  }, [zone, pollingMs]); // eslint-disable-line react-hooks/exhaustive-deps

  return {
    couriers: liveMap.data?.couriers ?? [],
    count:    liveMap.data?.count    ?? 0,
    loading:  liveMap.loading,
    error:    liveMap.error,
  };
}

/**
 * Hook para paginación declarativa de cualquier recurso listable.
 *
 * @param {Function} fetchFn    - Función de fetch del hook principal (ej. fetchTransactions)
 * @param {object}   baseFilters - Filtros fijos (no paginación)
 *
 * @example
 *   const { page, nextPage, prevPage } = usePagination(fetchTransactions, { currency: "MAD" })
 */
export function usePagination(fetchFn, baseFilters = {}) {
  const [page, setPage] = useState(1);

  const goTo = useCallback(
    (newPage) => {
      setPage(newPage);
      fetchFn({ ...baseFilters, page: newPage });
    },
    [fetchFn, JSON.stringify(baseFilters)] // eslint-disable-line react-hooks/exhaustive-deps
  );

  useEffect(() => {
    fetchFn({ ...baseFilters, page: 1 });
    setPage(1);
  }, [JSON.stringify(baseFilters)]); // eslint-disable-line react-hooks/exhaustive-deps

  return {
    page,
    nextPage: () => goTo(page + 1),
    prevPage: () => goTo(Math.max(1, page - 1)),
    goTo,
  };
}
