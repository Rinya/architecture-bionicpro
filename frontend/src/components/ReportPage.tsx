import React, { useState, useEffect } from 'react';
import { useKeycloak } from '@react-keycloak/web';
import UserSummary from './UserSummary';
import ReportPreview from './ReportPreview';
import LoadingSpinner from './LoadingSpinner';
import ErrorMessage from './ErrorMessage';
import SuccessMessage from './SuccessMessage';
import HelpSection from './HelpSection';

// Типы для работы с данными отчётов
interface ReportData {
  user_id: string;
  period: {
    start_date: string;
    end_date: string;
  };
  cached: boolean;
  summary: {
    total_days: number;
    total_usage_hours: number;
    avg_movement_efficiency: number;
    avg_maintenance_score: number;
    avg_battery_health: number;
    total_anomalies: number;
    total_sessions: number;
  };
  trends: {
    usage_trend: string;
    efficiency_trend: string;
    battery_trend: string;
  };
  recommendations: Array<{
    type: string;
    priority: string;
    title: string;
    message: string;
    action: string;
  }>;
  daily_reports: Array<{
    report_date: string;
    device_id: string;
    daily_usage_hours: number;
    movement_efficiency: number;
    maintenance_score: number;
    battery_health: number;
    anomaly_count: number;
    total_sessions: number;
    avg_session_duration: number;
    max_pressure_reached: number;
    last_sync: string;
  }>;
}

interface DeviceInfo {
  device_id: string;
  last_report_date: string;
  total_reports: number;
}

const ReportPage: React.FC = () => {
  const { keycloak, initialized } = useKeycloak();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [reportData, setReportData] = useState<ReportData | null>(null);
  const [devices, setDevices] = useState<DeviceInfo[]>([]);

  // Фильтры для отчётов
  const [startDate, setStartDate] = useState(() => {
    const date = new Date();
    date.setDate(date.getDate() - 30);
    return date.toISOString().split('T')[0];
  });
  const [endDate, setEndDate] = useState(() => {
    return new Date().toISOString().split('T')[0];
  });
  const [selectedDevice, setSelectedDevice] = useState<string>('');
  const [reportFormat, setReportFormat] = useState<'json' | 'pdf' | 'excel'>('json');

  // Получение ID пользователя из Keycloak токена
  const getUserId = () => {
    if (!keycloak?.tokenParsed) return null;
    return keycloak.tokenParsed.preferred_username || keycloak.tokenParsed.sub || 'user1';
  };

  // Загрузка списка устройств пользователя
  const loadUserDevices = async () => {
    const userId = getUserId();
    if (!userId || !keycloak?.token) return;

    try {
      const response = await fetch(`${process.env.REACT_APP_API_URL}/reports/${userId}/devices`, {
        headers: {
          'Authorization': `Bearer ${keycloak.token}`
        }
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      setDevices(data.devices || []);
    } catch (err) {
      console.error('Error loading devices:', err);
    }
  };

  // Основная функция загрузки отчёта
  const downloadReport = async () => {
    const userId = getUserId();
    if (!keycloak?.token || !userId) {
      setError('Не выполнена аутентификация');
      return;
    }

    try {
      setLoading(true);
      setError(null);
      setSuccess(null);

      // Формирование параметров запроса
      const params = new URLSearchParams({
        start_date: startDate,
        end_date: endDate,
        format: reportFormat
      });

      if (selectedDevice) {
        params.append('device_id', selectedDevice);
      }

      const response = await fetch(
        `${process.env.REACT_APP_API_URL}/reports/${userId}?${params.toString()}`,
        {
          headers: {
            'Authorization': `Bearer ${keycloak.token}`,
            'Accept': 'application/json'
          }
        }
      );

      if (!response.ok) {
        const errorData = await response.json();

        // Специальная обработка ошибок доступности данных
        if (response.status === 400 && errorData.available_until) {
          setError(
            `${errorData.message}\n\nДоступны данные до: ${new Date(errorData.available_until).toLocaleDateString('ru-RU')}\n\nПопробуйте изменить период запроса.`
          );
        } else {
          throw new Error(errorData.message || `HTTP ${response.status}: ${response.statusText}`);
        }
        return;
      }

      if (reportFormat === 'json') {
        const data: ReportData = await response.json();
        setReportData(data);
        setSuccess(`Отчёт загружен успешно. Найдено данных за ${data.summary.total_days} дней.`);
      } else {
        // Для PDF/Excel форматов
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.style.display = 'none';
        a.href = url;
        a.download = `bionicpro_report_${userId}_${startDate}_${endDate}.${reportFormat}`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        setSuccess(`Отчёт в формате ${reportFormat.toUpperCase()} успешно скачан.`);
      }

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Произошла ошибка при загрузке отчёта');
    } finally {
      setLoading(false);
    }
  };

  // Функция экспорта отчёта в другом формате
  const exportReport = async (format: 'pdf' | 'excel') => {
    const userId = getUserId();
    if (!keycloak?.token || !userId) {
      setError('Не выполнена аутентификация');
      return;
    }

    try {
      setLoading(true);
      setError(null);

      const params = new URLSearchParams({
        start_date: startDate,
        end_date: endDate,
        format: format
      });

      if (selectedDevice) {
        params.append('device_id', selectedDevice);
      }

      const response = await fetch(
        `${process.env.REACT_APP_API_URL}/reports/${userId}?${params.toString()}`,
        {
          headers: {
            'Authorization': `Bearer ${keycloak.token}`
          }
        }
      );

      if (!response.ok) {
        const errorData = await response.json();

        // Специальная обработка ошибок доступности данных
        if (response.status === 400 && errorData.available_until) {
          setError(
            `${errorData.message}\n\nДоступны данные до: ${new Date(errorData.available_until).toLocaleDateString('ru-RU')}`
          );
        } else {
          throw new Error(errorData.message || `Ошибка экспорта: HTTP ${response.status}`);
        }
        return;
      }

      // Скачивание файла
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.style.display = 'none';
      a.href = url;
      a.download = `bionicpro_report_${userId}_${startDate}_${endDate}.${format}`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);

      setSuccess(`Отчёт в формате ${format.toUpperCase()} успешно скачан.`);

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Произошла ошибка при экспорте');
    } finally {
      setLoading(false);
    }
  };

  // Загрузка устройств при инициализации
  useEffect(() => {
    if (initialized && keycloak.authenticated) {
      loadUserDevices();
    }
  }, [initialized, keycloak.authenticated]);

  if (!initialized) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-100">
        <LoadingSpinner message="Инициализация системы..." size="large" />
      </div>
    );
  }

  if (!keycloak.authenticated) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen bg-gray-100">
        <div className="p-8 bg-white rounded-lg shadow-md text-center">
          <h1 className="text-2xl font-bold mb-4 text-gray-800">BionicPRO Отчёты</h1>
          <p className="mb-6 text-gray-600">
            Войдите в систему для доступа к отчётам о работе ваших протезов
          </p>
          <button
            onClick={() => keycloak.login()}
            className="px-6 py-3 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
          >
            Войти через Keycloak
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-100 py-6">
      <div className="max-w-6xl mx-auto px-4">

        {/* Заголовок */}
        <div className="bg-white rounded-lg shadow-md p-6 mb-6">
          <div className="flex justify-between items-start">
            <div>
              <h1 className="text-3xl font-bold text-gray-800 mb-2">
                BionicPRO Отчёты
              </h1>
              <p className="text-gray-600 mb-2">
                Добро пожаловать, {keycloak.tokenParsed?.preferred_username || 'Пользователь'}
              </p>
              <div className="text-sm text-gray-500">
                <p className="flex items-center mb-1">
                  <span className="w-2 h-2 bg-green-500 rounded-full mr-2"></span>
                  Безопасное подключение через Keycloak
                </p>
                <p className="flex items-center">
                  <span className="w-2 h-2 bg-blue-500 rounded-full mr-2"></span>
                  Данные доступны только владельцу устройств
                </p>
              </div>
            </div>
            <div className="text-right">
              <div className="text-xs text-gray-500 mb-2">
                Сессия истекает: {
                  keycloak.tokenParsed?.exp ?
                  new Date(keycloak.tokenParsed.exp * 1000).toLocaleTimeString('ru-RU') :
                  'Неизвестно'
                }
              </div>
              <button
                onClick={() => keycloak.logout()}
                className="px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600 transition-colors text-sm"
              >
                Выйти
              </button>
            </div>
          </div>
        </div>

        {/* Сводка пользователя */}
        <UserSummary userId={getUserId() || ''} />

        {/* Справочная информация */}
        <HelpSection />

        {/* Фильтры и настройки отчёта */}
        <div className="bg-white rounded-lg shadow-md p-6 mb-6">
          <h2 className="text-xl font-semibold mb-4 text-gray-800">Параметры отчёта</h2>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">

            {/* Начальная дата */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Начальная дата
              </label>
              <input
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            {/* Конечная дата */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Конечная дата
              </label>
              <input
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            {/* Выбор устройства */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Устройство
              </label>
              <select
                value={selectedDevice}
                onChange={(e) => setSelectedDevice(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">Все устройства</option>
                {devices.map(device => (
                  <option key={device.device_id} value={device.device_id}>
                    {device.device_id} ({device.total_reports} отчётов)
                  </option>
                ))}
              </select>
            </div>

            {/* Формат отчёта */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Формат
              </label>
              <select
                value={reportFormat}
                onChange={(e) => setReportFormat(e.target.value as 'json' | 'pdf' | 'excel')}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="json">JSON (просмотр)</option>
                <option value="pdf">PDF (скачать)</option>
                <option value="excel">Excel (скачать)</option>
              </select>
            </div>
          </div>

          {/* Информация о доступности данных */}
          <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
            <div className="flex items-center">
              <svg className="w-5 h-5 text-blue-600 mr-2" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
              </svg>
              <div className="text-sm text-blue-700">
                <strong>Доступность данных:</strong> Система ETL обрабатывает данные каждые 15 минут.
                Данные за сегодня могут быть ещё не полными. Для полных отчётов рекомендуется
                запрашивать данные за вчера и ранее.
              </div>
            </div>
          </div>

          {/* Кнопка генерации отчёта */}
          <div className="text-center">
            <button
              onClick={downloadReport}
              disabled={loading}
              className={`px-8 py-3 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors ${
                loading ? 'opacity-50 cursor-not-allowed' : ''
              }`}
            >
              {loading ? (
                <div className="flex items-center">
                  <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white mr-2"></div>
                  Генерация отчёта...
                </div>
              ) : (
                reportFormat === 'json' ? 'Показать отчёт' : 'Скачать отчёт'
              )}
            </button>
          </div>
        </div>

        {/* Сообщение об успехе */}
        {success && (
          <SuccessMessage
            message={success}
            onDismiss={() => setSuccess(null)}
          />
        )}

        {/* Сообщение об ошибке */}
        {error && (
          <ErrorMessage
            message={error}
            type="error"
            onDismiss={() => setError(null)}
          />
        )}

        {/* Отображение данных отчёта (только для JSON формата) */}
        {reportData && reportFormat === 'json' && (
          <ReportPreview reportData={reportData} onExport={exportReport} />
        )}

        {/* Индикатор загрузки для генерации отчёта */}
        {loading && !reportData && (
          <div className="bg-white rounded-lg shadow-md p-6">
            <LoadingSpinner
              message={
                reportFormat === 'json' ? 'Загрузка данных отчёта...' :
                `Генерация ${reportFormat.toUpperCase()} отчёта...`
              }
              size="medium"
            />
          </div>
        )}

      </div>
    </div>
  );
};

export default ReportPage;