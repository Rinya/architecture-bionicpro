import React from 'react';

interface Props {
  message?: string;
  size?: 'small' | 'medium' | 'large';
}

const LoadingSpinner: React.FC<Props> = ({
  message = 'Загрузка...',
  size = 'medium'
}) => {
  const sizeClasses = {
    small: 'h-6 w-6',
    medium: 'h-8 w-8',
    large: 'h-12 w-12'
  };

  return (
    <div className="flex flex-col items-center justify-center py-8">
      <div className={`animate-spin rounded-full border-b-2 border-blue-500 ${sizeClasses[size]} mb-4`}></div>
      <p className="text-gray-600 text-center">{message}</p>
    </div>
  );
};

export default LoadingSpinner;