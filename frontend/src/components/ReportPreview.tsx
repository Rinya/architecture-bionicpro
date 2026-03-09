import React from 'react';

// Типы для компонента превью отчёта
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
  trends?: {
    usage_trend: string;
    efficiency_trend: string;
    battery_trend: string;
  };
  recommendations?: Array<{
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

interface Props {
  reportData: ReportData;
  onExport: (format: 'pdf' | 'excel') => void;
}

const ReportPreview: React.FC<Props> = ({ reportData, onExport }) => {

  const getTrendIcon = (trend: string) => {
    switch (trend) {
      case 'improving': return '📈';
      case 'declining': return '📉';
      default: return '📊';
    }
  };

  const getTrendText = (trend: string) => {
    switch (trend) {
      case 'improving': return 'Улучшается';
      case 'declining': return 'Ухудшается';
      default: return 'Стабильно';
    }
  };

  const getTrendColor = (trend: string) => {
    switch (trend) {
      case 'improving': return 'text-green-600 bg-green-50';
      case 'declining': return 'text-red-600 bg-red-50';
      default: return 'text-gray-600 bg-gray-50';
    }
  };

  return (
    <div className="space-y-6">

      {/* Заголовок с возможностью экспорта */}
      <div className="bg-white rounded-lg shadow-md p-6">
        <div className="flex justify-between items-center">
          <div>
            <h2 className="text-2xl font-bold text-gray-800">
              Отчёт о работе протеза
              {reportData.cached && (
                <span className="text-sm text-green-600 ml-2 font-normal">(Кэшированные данные)</span>
              )}
            </h2>
            <p className="text-gray-600 mt-2">
              Период: {new Date(reportData.period.start_date).toLocaleDateString('ru-RU')} —
              {new Date(reportData.period.end_date).toLocaleDateString('ru-RU')}
            </p>
          </div>
          <div className="flex space-x-2">
            <button
              onClick={() => onExport('pdf')}
              className="px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600 transition-colors text-sm"
            >
              📄 Скачать PDF
            </button>
            <button
              onClick={() => onExport('excel')}
              className="px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600 transition-colors text-sm"
            >
              📊 Скачать Excel
            </button>
          </div>
        </div>
      </div>

      {/* Сводка показателей */}
      <div className="bg-white rounded-lg shadow-md p-6">
        <h3 className="text-lg font-semibold text-gray-800 mb-4">📊 Основные показатели</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="text-center p-4 bg-blue-50 rounded-lg border">
            <div className="text-3xl font-bold text-blue-600">{reportData.summary.total_days}</div>
            <div className="text-sm text-gray-600 mt-1">Дней с данными</div>
          </div>
          <div className="text-center p-4 bg-purple-50 rounded-lg border">
            <div className="text-3xl font-bold text-purple-600">{reportData.summary.total_usage_hours}ч</div>
            <div className="text-sm text-gray-600 mt-1">Общее использование</div>
          </div>
          <div className="text-center p-4 bg-green-50 rounded-lg border">
            <div className="text-3xl font-bold text-green-600">{reportData.summary.avg_movement_efficiency}%</div>
            <div className="text-sm text-gray-600 mt-1">Эффективность</div>
          </div>
          <div className="text-center p-4 bg-orange-50 rounded-lg border">
            <div className="text-3xl font-bold text-orange-600">{reportData.summary.avg_battery_health}%</div>
            <div className="text-sm text-gray-600 mt-1">Здоровье батареи</div>
          </div>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mt-4">
          <div className="text-center p-4 bg-indigo-50 rounded-lg border">
            <div className="text-2xl font-bold text-indigo-600">{reportData.summary.avg_maintenance_score}%</div>
            <div className="text-sm text-gray-600 mt-1">Техсостояние</div>
          </div>
          <div className="text-center p-4 bg-teal-50 rounded-lg border">
            <div className="text-2xl font-bold text-teal-600">{reportData.summary.total_sessions}</div>
            <div className="text-sm text-gray-600 mt-1">Всего сессий</div>
          </div>
          <div className="text-center p-4 bg-yellow-50 rounded-lg border">
            <div className={`text-2xl font-bold ${
              reportData.summary.total_anomalies === 0 ? 'text-green-600' :
              reportData.summary.total_anomalies < 10 ? 'text-yellow-600' : 'text-red-600'
            }`}>
              {reportData.summary.total_anomalies}
            </div>
            <div className="text-sm text-gray-600 mt-1">Аномалий</div>
          </div>
        </div>
      </div>

      {/* Тренды */}
      {reportData.trends && Object.keys(reportData.trends).length > 0 && (
        <div className="bg-white rounded-lg shadow-md p-6">
          <h3 className="text-lg font-semibold text-gray-800 mb-4">📈 Тренды показателей</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="text-center">
              <div className={`inline-flex items-center px-4 py-2 rounded-lg ${getTrendColor(reportData.trends.usage_trend)}`}>
                <span className="text-2xl mr-2">{getTrendIcon(reportData.trends.usage_trend)}</span>
                <div>
                  <div className="font-semibold">Использование</div>
                  <div className="text-sm">{getTrendText(reportData.trends.usage_trend)}</div>
                </div>
              </div>
            </div>
            <div className="text-center">
              <div className={`inline-flex items-center px-4 py-2 rounded-lg ${getTrendColor(reportData.trends.efficiency_trend)}`}>
                <span className="text-2xl mr-2">{getTrendIcon(reportData.trends.efficiency_trend)}</span>
                <div>
                  <div className="font-semibold">Эффективность</div>
                  <div className="text-sm">{getTrendText(reportData.trends.efficiency_trend)}</div>
                </div>
              </div>
            </div>
            <div className="text-center">
              <div className={`inline-flex items-center px-4 py-2 rounded-lg ${getTrendColor(reportData.trends.battery_trend)}`}>
                <span className="text-2xl mr-2">{getTrendIcon(reportData.trends.battery_trend)}</span>
                <div>
                  <div className="font-semibold">Батарея</div>
                  <div className="text-sm">{getTrendText(reportData.trends.battery_trend)}</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Рекомендации */}
      {reportData.recommendations && reportData.recommendations.length > 0 && (
        <div className="bg-white rounded-lg shadow-md p-6">
          <h3 className="text-lg font-semibold text-gray-800 mb-4">💡 Рекомендации</h3>
          <div className="space-y-4">
            {reportData.recommendations.map((rec, index) => (
              <div
                key={index}
                className={`p-4 rounded-lg border-l-4 ${
                  rec.priority === 'high' ? 'border-red-500 bg-red-50' :
                  rec.priority === 'medium' ? 'border-yellow-500 bg-yellow-50' :
                  'border-blue-500 bg-blue-50'
                }`}
              >
                <div className="flex items-start space-x-3">
                  <span className="text-2xl">
                    {rec.priority === 'high' ? '🚨' : rec.priority === 'medium' ? '⚠️' : 'ℹ️'}
                  </span>
                  <div className="flex-1">
                    <div className="flex justify-between items-start">
                      <div>
                        <h4 className="font-semibold text-gray-800">{rec.title}</h4>
                        <p className="text-gray-600 text-sm mt-1">{rec.message}</p>
                        <p className="text-gray-500 text-xs mt-2 font-medium">
                          Действие: {rec.action}
                        </p>
                      </div>
                      <span
                        className={`px-3 py-1 rounded-full text-xs font-medium ${
                          rec.priority === 'high' ? 'bg-red-100 text-red-800' :
                          rec.priority === 'medium' ? 'bg-yellow-100 text-yellow-800' :
                          'bg-blue-100 text-blue-800'
                        }`}
                      >
                        {rec.priority === 'high' ? 'Высокий приоритет' :
                         rec.priority === 'medium' ? 'Средний приоритет' : 'Низкий приоритет'}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Детальные данные */}
      {reportData.daily_reports && reportData.daily_reports.length > 0 && (
        <div className="bg-white rounded-lg shadow-md p-6">
          <h3 className="text-lg font-semibold text-gray-800 mb-4">📅 Детальные данные по дням</h3>

          {reportData.daily_reports.length > 10 && (
            <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
              <p className="text-sm text-blue-700">
                📊 Показано {reportData.daily_reports.length} записей.
                Полная таблица доступна в экспортированном файле.
              </p>
            </div>
          )}

          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Дата
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Устройство
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Время (ч)
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Эффективность
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Батарея
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Сессии
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Аномалии
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {reportData.daily_reports.slice(0, 15).map((report, index) => (
                  <tr key={`${report.report_date}-${report.device_id}`} className={index % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                    <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-900 font-medium">
                      {new Date(report.report_date).toLocaleDateString('ru-RU')}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-600">
                      {report.device_id}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-900 font-medium">
                      {report.daily_usage_hours}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm">
                      <span className={`inline-flex px-2 py-1 rounded-full text-xs font-medium ${
                        report.movement_efficiency >= 80 ? 'bg-green-100 text-green-800' :
                        report.movement_efficiency >= 60 ? 'bg-yellow-100 text-yellow-800' :
                        'bg-red-100 text-red-800'
                      }`}>
                        {report.movement_efficiency}%
                      </span>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm">
                      <span className={`inline-flex px-2 py-1 rounded-full text-xs font-medium ${
                        report.battery_health >= 80 ? 'bg-green-100 text-green-800' :
                        report.battery_health >= 60 ? 'bg-yellow-100 text-yellow-800' :
                        'bg-red-100 text-red-800'
                      }`}>
                        {report.battery_health}%
                      </span>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-900">
                      {report.total_sessions}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm">
                      {report.anomaly_count > 0 ? (
                        <span className="inline-flex px-2 py-1 rounded-full text-xs font-medium bg-red-100 text-red-800">
                          {report.anomaly_count}
                        </span>
                      ) : (
                        <span className="text-gray-400">—</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {reportData.daily_reports.length > 15 && (
            <div className="mt-4 text-center">
              <p className="text-sm text-gray-500">
                и ещё {reportData.daily_reports.length - 15} записей...
              </p>
            </div>
          )}
        </div>
      )}

      {/* Пустое состояние */}
      {reportData.daily_reports.length === 0 && (
        <div className="bg-white rounded-lg shadow-md p-6 text-center">
          <div className="text-gray-400 mb-4">
            <svg className="w-16 h-16 mx-auto" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M3 4a1 1 0 011-1h12a1 1 0 011 1v2a1 1 0 01-1 1H4a1 1 0 01-1-1V4zM3 10a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H4a1 1 0 01-1-1v-6zM14 9a1 1 0 00-1 1v6a1 1 0 001 1h2a1 1 0 001-1v-6a1 1 0 00-1-1h-2z" clipRule="evenodd" />
            </svg>
          </div>
          <h3 className="text-lg font-semibold text-gray-600 mb-2">Нет данных за указанный период</h3>
          <p className="text-gray-500">Попробуйте выбрать другой период или проверьте подключение устройств</p>
        </div>
      )}
    </div>
  );
};

export default ReportPreview;