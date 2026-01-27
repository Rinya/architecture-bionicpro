import React, { useEffect } from 'react';

interface Props {
  message: string;
  onDismiss?: () => void;
  autoHide?: boolean;
  autoHideDelay?: number;
}

const SuccessMessage: React.FC<Props> = ({
  message,
  onDismiss,
  autoHide = true,
  autoHideDelay = 5000
}) => {

  useEffect(() => {
    if (autoHide && onDismiss) {
      const timer = setTimeout(() => {
        onDismiss();
      }, autoHideDelay);

      return () => clearTimeout(timer);
    }
  }, [autoHide, autoHideDelay, onDismiss]);

  return (
    <div className="bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded-lg mb-6">
      <div className="flex items-start">
        <div className="flex-shrink-0 mr-3 mt-0.5">
          <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
          </svg>
        </div>
        <div className="flex-grow">
          <div className="font-medium">Успешно</div>
          <div className="mt-1 text-sm">{message}</div>
        </div>
        {onDismiss && (
          <button
            onClick={onDismiss}
            className="flex-shrink-0 ml-3 text-lg font-bold opacity-70 hover:opacity-100 transition-opacity"
          >
            ×
          </button>
        )}
      </div>
    </div>
  );
};

export default SuccessMessage;