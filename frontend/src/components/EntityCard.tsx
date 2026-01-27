import React from 'react';
import type { EntityCardProps } from '../types';
import { User, Building, Globe, Server, Mail, Phone, MapPin, Calendar } from 'lucide-react';

const EntityCard: React.FC<EntityCardProps> = ({
  entity,
  onClick,
  onEdit,
  onDelete,
  compact = false
}) => {
  const showActions = !compact;
  const getEntityIcon = (type: string) => {
    switch (type) {
      case 'person':
        return <User className="w-5 h-5" />;
      case 'organization':
        return <Building className="w-5 h-5" />;
      case 'domain':
        return <Globe className="w-5 h-5" />;
      case 'ip':
        return <Server className="w-5 h-5" />;
      case 'email':
        return <Mail className="w-5 h-5" />;
      case 'phone':
        return <Phone className="w-5 h-5" />;
      case 'location':
        return <MapPin className="w-5 h-5" />;
      default:
        return <User className="w-5 h-5" />;
    }
  };

  const getEntityTypeColor = (type: string) => {
    switch (type) {
      case 'person':
        return 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300';
      case 'organization':
        return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300';
      case 'domain':
        return 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-300';
      case 'ip':
        return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300';
      case 'email':
        return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300';
      case 'phone':
        return 'bg-indigo-100 text-indigo-800 dark:bg-indigo-900 dark:text-indigo-300';
      case 'location':
        return 'bg-pink-100 text-pink-800 dark:bg-pink-900 dark:text-pink-300';
      default:
        return 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-300';
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('es-ES', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  };

  const handleCardClick = () => {
    if (onClick) {
      onClick(entity);
    }
  };

  const handleEdit = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (onEdit) {
      onEdit(entity);
    }
  };

  const handleDelete = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (onDelete) {
      onDelete(entity);
    }
  };

  return (
    <div 
      className={`bg-white dark:bg-gray-800 rounded-lg shadow-md border border-gray-200 dark:border-gray-700 p-4 transition-all duration-200 hover:shadow-lg hover:border-blue-300 dark:hover:border-blue-600 ${
        onClick ? 'cursor-pointer' : ''
      }`}
      onClick={handleCardClick}
    >
      {/* Header con icono y tipo */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center space-x-2">
          <div className="text-gray-600 dark:text-gray-400">
            {getEntityIcon(entity.type)}
          </div>
          <span className={`px-2 py-1 rounded-full text-xs font-medium ${getEntityTypeColor(entity.type)}`}>
            {entity.type.charAt(0).toUpperCase() + entity.type.slice(1)}
          </span>
        </div>
        
        {showActions && (
          <div className="flex space-x-1">
            {onEdit && (
              <button
                onClick={handleEdit}
                className="p-1 text-gray-400 hover:text-blue-600 dark:hover:text-blue-400 transition-colors"
                title="Editar entidad"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                </svg>
              </button>
            )}
            {onDelete && (
              <button
                onClick={handleDelete}
                className="p-1 text-gray-400 hover:text-red-600 dark:hover:text-red-400 transition-colors"
                title="Eliminar entidad"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
              </button>
            )}
          </div>
        )}
      </div>

      {/* Nombre de la entidad */}
      <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2 truncate">
        {entity.name}
      </h3>

      {/* Descripción si existe */}
      {entity.description && (
        <p className="text-sm text-gray-600 dark:text-gray-400 mb-3 line-clamp-2">
          {entity.description}
        </p>
      )}

      {/* Propiedades principales */}
      {entity.properties && Object.keys(entity.properties).length > 0 && (
        <div className="mb-3">
          <div className="flex flex-wrap gap-1">
            {Object.entries(entity.properties).slice(0, 3).map(([key, value]) => (
              <span 
                key={key}
                className="inline-flex items-center px-2 py-1 rounded text-xs bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300"
              >
                <span className="font-medium">{key}:</span>
                <span className="ml-1 truncate max-w-20">{String(value)}</span>
              </span>
            ))}
            {Object.keys(entity.properties).length > 3 && (
              <span className="inline-flex items-center px-2 py-1 rounded text-xs bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300">
                +{Object.keys(entity.properties).length - 3} más
              </span>
            )}
          </div>
        </div>
      )}

      {/* Footer con fecha */}
      <div className="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
        <div className="flex items-center space-x-1">
          <Calendar className="w-3 h-3" />
          <span>Creado: {(entity.created_at || entity.createdAt) ? formatDate((entity.created_at || entity.createdAt)!) : 'N/A'}</span>
        </div>
        {(entity.updated_at || entity.updatedAt) !== (entity.created_at || entity.createdAt) && (
          <span>Actualizado: {(entity.updated_at || entity.updatedAt) ? formatDate((entity.updated_at || entity.updatedAt)!) : 'N/A'}</span>
        )}
      </div>
    </div>
  );
};

export default EntityCard;