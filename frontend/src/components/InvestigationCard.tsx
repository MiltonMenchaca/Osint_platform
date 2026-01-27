import React from 'react';
import type { Investigation } from '../types';
import {
  Calendar,
  User,
  Tag,
  BarChart3,
  Eye,
  Edit,
  Trash2
} from 'lucide-react';

interface InvestigationCardProps {
  investigation: Investigation;
  onView?: (investigation: Investigation) => void;
  onEdit?: (investigation: Investigation) => void;
  onDelete?: (investigationId: string) => void;
  viewMode?: 'grid' | 'list';
  className?: string;
}

const InvestigationCard: React.FC<InvestigationCardProps> = ({
  investigation,
  onView,
  onEdit,
  onDelete,
  viewMode = 'grid',
  className = ''
}) => {
  const getStatusColor = (status: Investigation['status']) => {
    switch (status) {
      case 'active':
        return 'bg-green-100 text-green-800 border-green-200';
      case 'completed':
        return 'bg-blue-100 text-blue-800 border-blue-200';
      case 'archived':
        return 'bg-gray-100 text-gray-800 border-gray-200';
      default:
        return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  const getPriorityColor = (priority: Investigation['priority']) => {
    switch (priority) {
      case 'critical':
        return 'bg-red-100 text-red-800 border-red-200';
      case 'high':
        return 'bg-orange-100 text-orange-800 border-orange-200';
      case 'medium':
        return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      case 'low':
        return 'bg-green-100 text-green-800 border-green-200';
      default:
        return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('es-ES', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  };

  const getStatusText = (status: Investigation['status']) => {
    switch (status) {
      case 'active': return 'Activa';
      case 'completed': return 'Completada';
      case 'archived': return 'Archivada';
      default: return status;
    }
  };

  const getPriorityText = (priority: Investigation['priority']) => {
    switch (priority) {
      case 'critical': return 'Crítica';
      case 'high': return 'Alta';
      case 'medium': return 'Media';
      case 'low': return 'Baja';
      default: return priority;
    }
  };

  return (
    <div className={`bg-white rounded-lg shadow-sm border border-gray-200 hover:shadow-md transition-shadow duration-200 ${
      viewMode === 'list' ? 'flex items-center p-3' : 'p-4'
    } ${className}`}>
      {/* Header */}
      <div className={`flex justify-between items-start ${viewMode === 'list' ? 'flex-1' : 'mb-3'}`}>
        <div className="flex-1">
          <h3 className={`font-semibold text-gray-900 ${viewMode === 'list' ? 'text-base mb-1' : 'text-lg mb-2'} line-clamp-2`}>
            {investigation.title}
          </h3>
          <p className={`text-sm text-gray-600 ${viewMode === 'list' ? 'line-clamp-1' : 'line-clamp-3'}`}>
            {investigation.description}
          </p>
        </div>
        
        <div className="flex space-x-1 ml-4">
          {onView && (
            <button
              onClick={() => onView(investigation)}
              className="p-2 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded-md transition-colors"
              title="Ver detalles"
            >
              <Eye className="h-4 w-4" />
            </button>
          )}
          {onEdit && (
            <button
              onClick={() => onEdit(investigation)}
              className="p-2 text-gray-400 hover:text-green-600 hover:bg-green-50 rounded-md transition-colors"
              title="Editar"
            >
              <Edit className="h-4 w-4" />
            </button>
          )}
          {onDelete && (
            <button
              onClick={() => onDelete(investigation.id)}
              className="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-md transition-colors"
              title="Eliminar"
            >
              <Trash2 className="h-4 w-4" />
            </button>
          )}
        </div>
      </div>

      {/* Status and Priority Badges */}
      {viewMode === 'grid' && (
        <div className="flex flex-wrap gap-2 mb-3">
          <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${getStatusColor(investigation.status)}`}>
            <Tag className="h-3 w-3 mr-1" />
            {getStatusText(investigation.status)}
          </span>
          <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${getPriorityColor(investigation.priority)}`}>
            {getPriorityText(investigation.priority)}
          </span>
        </div>
      )}

      {/* Metadata */}
      <div className={`flex flex-wrap items-center gap-3 text-sm text-gray-500 ${viewMode === 'list' ? 'ml-3' : ''}`}>
        {viewMode === 'list' && (
          <>
            <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${getStatusColor(investigation.status)}`}>
              {getStatusText(investigation.status)}
            </span>
            <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${getPriorityColor(investigation.priority)}`}>
              {getPriorityText(investigation.priority)}
            </span>
          </>
        )}
        
        <div className="flex items-center">
          <BarChart3 className="h-4 w-4 mr-1" />
          <span>{investigation.entities?.length || 0} entidades</span>
        </div>
        
        <div className="flex items-center">
          <User className="h-4 w-4 mr-1" />
          <span>Por: {investigation.createdBy}</span>
        </div>
        
        <div className="flex items-center">
          <Calendar className="h-4 w-4 mr-1" />
          <span>Creada: {formatDate(investigation.createdAt)}</span>
        </div>
      </div>

      {/* Updated date if different from created */}
      {investigation.updatedAt !== investigation.createdAt && viewMode === 'grid' && (
        <div className="mt-2 text-xs text-gray-400">
          Actualizada: {formatDate(investigation.updatedAt)}
        </div>
      )}
    </div>
  );
};

export default InvestigationCard;