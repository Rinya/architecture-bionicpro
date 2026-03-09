import React, { useState } from 'react';

const HelpSection: React.FC = () => {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="bg-white rounded-lg shadow-md mb-6">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex justify-between items-center p-4 text-left hover:bg-gray-50 transition-colors rounded-lg"
      >
        <div className="flex items-center">
          <span className="text-lg mr-3">❓</span>
          <span className="font-medium text-gray-800">Справка по использованию отчётов</span>
        </div>
        <svg
          className={`w-5 h-5 transform transition-transform ${isOpen ? 'rotate-180' : ''}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {isOpen && (
        <div className="px-6 pb-6 border-t border-gray-200">
          <div className="grid md:grid-cols-2 gap-6 mt-4">

            {/* Левая колонка */}
            <div>
              <h3 className="font-semibold text-gray-800 mb-3">📊 О показателях</h3>
              <div className="space-y-2 text-sm text-gray-600">
                <div className="flex items-start">
                  <span className="w-2 h-2 bg-blue-500 rounded-full mr-2 mt-2 flex-shrink-0"></span>
                  <div>
                    <strong>Эффективность движений:</strong> Показывает, насколько точно протез
                    реагирует на мышечные сигналы (0-100%)
                  </div>
                </div>
                <div className="flex items-start">
                  <span className="w-2 h-2 bg-green-500 rounded-full mr-2 mt-2 flex-shrink-0"></span>
                  <div>
                    <strong>Здоровье батареи:</strong> Общее состояние аккумулятора и
                    системы питания (0-100%)
                  </div>
                </div>
                <div className="flex items-start">
                  <span className="w-2 h-2 bg-purple-500 rounded-full mr-2 mt-2 flex-shrink-0"></span>
                  <div>
                    <strong>Техническое состояние:</strong> Общая оценка работы всех систем
                    протеза (0-100%)
                  </div>
                </div>
                <div className="flex items-start">
                  <span className="w-2 h-2 bg-yellow-500 rounded-full mr-2 mt-2 flex-shrink-0"></span>
                  <div>
                    <strong>Аномалии:</strong> Количество нештатных ситуаций в работе
                    устройства
                  </div>
                </div>
              </div>
            </div>

            {/* Правая колонка */}
            <div>
              <h3 className="font-semibold text-gray-800 mb-3">🔧 Рекомендации</h3>
              <div className="space-y-2 text-sm text-gray-600">
                <div className="flex items-start">
                  <span className="text-green-500 mr-2 mt-1">✅</span>
                  <div>
                    <strong>80-100%:</strong> Отличные показатели, протез работает оптимально
                  </div>
                </div>
                <div className="flex items-start">
                  <span className="text-yellow-500 mr-2 mt-1">⚠️</span>
                  <div>
                    <strong>60-79%:</strong> Нормальная работа, возможны незначительные
                    корректировки
                  </div>
                </div>
                <div className="flex items-start">
                  <span className="text-red-500 mr-2 mt-1">🚨</span>
                  <div>
                    <strong>Ниже 60%:</strong> Рекомендуется обратиться в сервисный центр
                    для диагностики
                  </div>
                </div>
              </div>

              <h3 className="font-semibold text-gray-800 mb-3 mt-4">📥 Экспорт данных</h3>
              <div className="space-y-2 text-sm text-gray-600">
                <div>• <strong>JSON:</strong> Для просмотра в браузере</div>
                <div>• <strong>PDF:</strong> Для печати и архивирования</div>
                <div>• <strong>Excel:</strong> Для анализа в табличном редакторе</div>
              </div>
            </div>
          </div>

          <div className="mt-6 pt-4 border-t border-gray-200">
            <h3 className="font-semibold text-gray-800 mb-2">🔒 Безопасность</h3>
            <p className="text-sm text-gray-600">
              Ваши данные защищены современными методами шифрования. Доступ к отчётам
              предоставляется только после аутентификации через Keycloak и проверки
              прав доступа. Каждое обращение к данным логируется для безопасности.
            </p>
          </div>

          <div className="mt-4">
            <h3 className="font-semibold text-gray-800 mb-2">📞 Поддержка</h3>
            <p className="text-sm text-gray-600">
              Если у вас возникли вопросы по отчётам или проблемы с устройством,
              обратитесь в службу поддержки: <strong>support@bionicpro.com</strong>
            </p>
          </div>
        </div>
      )}
    </div>
  );
};

export default HelpSection;