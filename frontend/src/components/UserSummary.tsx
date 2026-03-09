import React, { useState, useEffect } from 'react';
import { useKeycloak } from '@react-keycloak/web';
import { makeAuthenticatedRequest, safeParseJson } from '../utils/tokenService';

interface UserSummaryData {
  user_id: string;
  period_days: number;
  total_days_with_data: number;
  total_usage_hours: number;
  avg_movement_efficiency: number;
  avg_maintenance_score: number;
  avg_battery_health: number;
  total_anomalies: number;
  total_sessions: number;
  last_activity: string;
}

interface Props {
  userId: string;
}

const UserSummary: React.FC<Props> = ({ userId }) => {
  const { keycloak } = useKeycloak();
  const [loading, setLoading] = useState(true);
  const [summaryData, setSummaryData] = useState<UserSummaryData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadSummary = async () => {
      if (!keycloak?.token || !userId) return;

      try {
        setLoading(true);
        setError(null);

        const response = await makeAuthenticatedRequest(
          `${process.env.REACT_APP_API_URL}/reports/${userId}/summary`,
          keycloak.token!
        );

        if (!response.ok) {
          const errorData = await safeParseJson(response);
          throw new Error(errorData.message || 'Ошибка загрузки сводки');
        }

        const data: UserSummaryData = await safeParseJson(response);
        setSummaryData(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Произошла ошибка');
      } finally {
        setLoading(false);
      }
    };

    loadSummary();
  }, [keycloak?.token, userId]);

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow-md p-6">
        <div className="animate-pulse">
          <div className="h-6 bg-gray-200 rounded mb-4"></div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="h-20 bg-gray-200 rounded"></div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white rounded-lg shadow-md p-6">
        <div className="text-center text-red-600">
          <p>Ошибка загрузки сводки: {error}</p>
        </div>
      </div>
    );
  }

  if (!summaryData) {
    return null;
  }

  const safeNumber = (value: number | null | undefined, defaultValue: number = 0): number => {
    if (value === null || value === undefined || isNaN(value) || !isFinite(value)) {
      return defaultValue;
    }
    return value;
  };

  const getScoreColor = (score: number, type: 'efficiency' | 'maintenance' | 'battery') => {
    const safeScore = safeNumber(score);
    if (safeScore >= 80) return 'text-green-600 bg-green-50';
    if (safeScore >= 60) return 'text-yellow-600 bg-yellow-50';
    return 'text-red-600 bg-red-50';
  };

  return (
    <div className="bg-white rounded-lg shadow-md p-6 mb-6">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-xl font-semibold text-gray-800">
          Сводка за последние {summaryData.period_days} дней
        </h2>
        {summaryData.last_activity && (
          <span className="text-sm text-gray-500">
            Последняя активность: {new Date(summaryData.last_activity).toLocaleDateString('ru-RU')}
          </span>
        )}
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-4">

        {/* Дни с данными */}
        <div className="col-span-1 text-center p-4 bg-blue-50 rounded-lg">
          <div className="text-2xl font-bold text-blue-600">
            {summaryData.total_days_with_data}
          </div>
          <div className="text-sm text-gray-600">Активных дней</div>
        </div>

        {/* Общее использование */}
        <div className="col-span-1 text-center p-4 bg-purple-50 rounded-lg">
          <div className="text-2xl font-bold text-purple-600">
            {safeNumber(summaryData.total_usage_hours)}ч
          </div>
          <div className="text-sm text-gray-600">Общее время</div>
        </div>

        {/* Эффективность движений */}
        <div className={`col-span-1 text-center p-4 rounded-lg ${getScoreColor(summaryData.avg_movement_efficiency, 'efficiency')}`}>
          <div className="text-2xl font-bold">
            {safeNumber(summaryData.avg_movement_efficiency)}%
          </div>
          <div className="text-sm">Эффективность</div>
        </div>

        {/* Техсостояние */}
        <div className={`col-span-1 text-center p-4 rounded-lg ${getScoreColor(summaryData.avg_maintenance_score, 'maintenance')}`}>
          <div className="text-2xl font-bold">
            {safeNumber(summaryData.avg_maintenance_score)}%
          </div>
          <div className="text-sm">Техсостояние</div>
        </div>

        {/* Здоровье батареи */}
        <div className={`col-span-1 text-center p-4 rounded-lg ${getScoreColor(summaryData.avg_battery_health, 'battery')}`}>
          <div className="text-2xl font-bold">
            {safeNumber(summaryData.avg_battery_health)}%
          </div>
          <div className="text-sm">Батарея</div>
        </div>

        {/* Общие сессии */}
        <div className="col-span-1 text-center p-4 bg-green-50 rounded-lg">
          <div className="text-2xl font-bold text-green-600">
            {summaryData.total_sessions}
          </div>
          <div className="text-sm text-gray-600">Сессий</div>
        </div>

        {/* Аномалии */}
        <div className={`col-span-1 text-center p-4 rounded-lg ${
          summaryData.total_anomalies === 0 ? 'bg-green-50' :
          summaryData.total_anomalies < 10 ? 'bg-yellow-50' : 'bg-red-50'
        }`}>
          <div className={`text-2xl font-bold ${
            summaryData.total_anomalies === 0 ? 'text-green-600' :
            summaryData.total_anomalies < 10 ? 'text-yellow-600' : 'text-red-600'
          }`}>
            {summaryData.total_anomalies}
          </div>
          <div className="text-sm text-gray-600">Аномалий</div>
        </div>

        {/* Соотношение активных дней */}
        <div className="col-span-1 text-center p-4 bg-indigo-50 rounded-lg">
          <div className="text-2xl font-bold text-indigo-600">
            {summaryData.period_days > 0 ? Math.round((summaryData.total_days_with_data / summaryData.period_days) * 100) : 0}%
          </div>
          <div className="text-sm text-gray-600">Активность</div>
        </div>
      </div>

      {/* Индикаторы состояния */}
      <div className="mt-6 pt-4 border-t border-gray-200">
        <div className="flex flex-wrap gap-2">

          {/* Общее состояние */}
          {safeNumber(summaryData.avg_movement_efficiency) >= 80 &&
           safeNumber(summaryData.avg_battery_health) >= 80 &&
           summaryData.total_anomalies < 5 && (
            <span className="px-3 py-1 bg-green-100 text-green-800 text-sm rounded-full">
              ✅ Отличное состояние
            </span>
          )}

          {safeNumber(summaryData.avg_movement_efficiency) < 70 && (
            <span className="px-3 py-1 bg-red-100 text-red-800 text-sm rounded-full">
              ⚠️ Требуется калибровка
            </span>
          )}

          {safeNumber(summaryData.avg_battery_health) < 70 && (
            <span className="px-3 py-1 bg-red-100 text-red-800 text-sm rounded-full">
              🔋 Проблемы с батареей
            </span>
          )}

          {summaryData.total_anomalies > 10 && (
            <span className="px-3 py-1 bg-red-100 text-red-800 text-sm rounded-full">
              🚨 Много аномалий
            </span>
          )}

          {safeNumber(summaryData.avg_maintenance_score) < 80 && (
            <span className="px-3 py-1 bg-yellow-100 text-yellow-800 text-sm rounded-full">
              🔧 Требуется обслуживание
            </span>
          )}
        </div>
      </div>
    </div>
  );
};

export default UserSummary;