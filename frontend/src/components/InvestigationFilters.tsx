import React from 'react';
import type { Investigation } from '../types';
import {
  Filter,
  X,
  Calendar,
  Tag,
  AlertTriangle
} from 'lucide-react';

export interface InvestigationFilters {
  status?: Investigation['status'][];
  priority?: Investigation['priority'][];
  dateRange?: {
    start?: string;
    end?: string;
  };
  search?: string;
  createdBy?: string;
}

interface InvestigationFiltersProps {
  filters: InvestigationFilters;
  onFiltersChange: (filters: InvestigationFilters) => void;
  onClearFilters: () => void;
  className?: string;
}

const InvestigationFiltersComponent: React.FC<InvestigationFiltersProps> = ({
  filters,
  onFiltersChange,
  onClearFilters,
  className = ''
}) => {
  const statusOptions: { value: Investigation['status']; label: string; color: string }[] = [
    { value: 'active', label: 'Activa', color: 'text-green-600' },
    { value: 'completed', label: 'Completada', color: 'text-blue-600' },
    { value: 'archived', label: 'Archivada', color: 'text-gray-600' }
  ];

  const priorityOptions: { value: Investigation['priority']; label: string; color: string }[] = [
    { value: 'critical', label: 'Crítica', color: 'text-red-600' },
    { value: 'high', label: 'Alta', color: 'text-orange-600' },
    { value: 'medium', label: 'Media', color: 'text-yellow-600' },
    { value: 'low', label: 'Baja', color: 'text-green-600' }
  ];

  const handleStatusChange = (status: Investigation['status'], checked: boolean) => {
    const currentStatus = filters.status || [];
    const newStatus = checked 
      ? [...currentStatus, status]
      : currentStatus.filter(s => s !== status);
    
    onFiltersChange({
      ...filters,
      status: newStatus.length > 0 ? newStatus : undefined
    });
  };

  const handlePriorityChange = (priority: Investigation['priority'], checked: boolean) => {
    const currentPriority = filters.priority || [];
    const newPriority = checked 
      ? [...currentPriority, priority]
      : currentPriority.filter(p => p !== priority);
    
    onFiltersChange({
      ...filters,
      priority: newPriority.length > 0 ? newPriority : undefined
    });
  };

  const handleDateRangeChange = (field: 'start' | 'end', value: string) => {
    onFiltersChange({
      ...filters,
      dateRange: {
        ...filters.dateRange,
        [field]: value || undefined
      }
    });
  };

  const handleSearchChange = (value: string) => {
    onFiltersChange({
      ...filters,
      search: value || undefined
    });
  };

  const handleCreatedByChange = (value: string) => {
    onFiltersChange({
      ...filters,
      createdBy: value || undefined
    });
  };

  const hasActiveFilters = () => {
    return !!(filters.status?.length || 
             filters.priority?.length || 
             filters.dateRange?.start || 
             filters.dateRange?.end || 
             filters.search || 
             filters.createdBy);
  };

  return (
    <div className={`bg-white rounded-lg shadow-sm border border-gray-200 p-4 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center">
          <Filter className="h-5 w-5 text-gray-500 mr-2" />
          <h3 className="text-lg font-medium text-gray-900">Filtros</h3>
        </div>
        
        {hasActiveFilters() && (
          <button
            onClick={onClearFilters}
            className="flex items-center text-sm text-gray-500 hover:text-red-600 transition-colors"
          >
            <X className="h-4 w-4 mr-1" />
            Limpiar filtros
          </button>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Search */}
        <div className="col-span-full">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Búsqueda
          </label>
          <input
            type="text"
            value={filters.search || ''}
            onChange={(e) => handleSearchChange(e.target.value)}
            placeholder="Buscar por título o descripción..."
            className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          />
        </div>

        {/* Status Filter */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            <Tag className="h-4 w-4 inline mr-1" />
            Estado
          </label>
          <div className="space-y-2">
            {statusOptions.map((option) => (
              <label key={option.value} className="flex items-center">
                <input
                  type="checkbox"
                  checked={filters.status?.includes(option.value) || false}
                  onChange={(e) => handleStatusChange(option.value, e.target.checked)}
                  className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                />
                <span className={`ml-2 text-sm ${option.color}`}>
                  {option.label}
                </span>
              </label>
            ))}
          </div>
        </div>

        {/* Priority Filter */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            <AlertTriangle className="h-4 w-4 inline mr-1" />
            Prioridad
          </label>
          <div className="space-y-2">
            {priorityOptions.map((option) => (
              <label key={option.value} className="flex items-center">
                <input
                  type="checkbox"
                  checked={filters.priority?.includes(option.value) || false}
                  onChange={(e) => handlePriorityChange(option.value, e.target.checked)}
                  className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                />
                <span className={`ml-2 text-sm ${option.color}`}>
                  {option.label}
                </span>
              </label>
            ))}
          </div>
        </div>

        {/* Date Range Filter */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            <Calendar className="h-4 w-4 inline mr-1" />
            Rango de fechas
          </label>
          <div className="space-y-2">
            <input
              type="date"
              value={filters.dateRange?.start || ''}
              onChange={(e) => handleDateRangeChange('start', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm"
              placeholder="Fecha inicio"
            />
            <input
              type="date"
              value={filters.dateRange?.end || ''}
              onChange={(e) => handleDateRangeChange('end', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm"
              placeholder="Fecha fin"
            />
          </div>
        </div>

        {/* Created By Filter */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Creado por
          </label>
          <input
            type="text"
            value={filters.createdBy || ''}
            onChange={(e) => handleCreatedByChange(e.target.value)}
            placeholder="Nombre de usuario..."
            className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm"
          />
        </div>
      </div>

      {/* Active Filters Summary */}
      {hasActiveFilters() && (
        <div className="mt-4 pt-4 border-t border-gray-200">
          <div className="flex flex-wrap gap-2">
            {filters.status?.map((status) => (
              <span key={status} className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                Estado: {statusOptions.find(s => s.value === status)?.label}
                <button
                  onClick={() => handleStatusChange(status, false)}
                  className="ml-1 h-3 w-3 text-blue-600 hover:text-blue-800"
                >
                  <X className="h-3 w-3" />
                </button>
              </span>
            ))}
            
            {filters.priority?.map((priority) => (
              <span key={priority} className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-orange-100 text-orange-800">
                Prioridad: {priorityOptions.find(p => p.value === priority)?.label}
                <button
                  onClick={() => handlePriorityChange(priority, false)}
                  className="ml-1 h-3 w-3 text-orange-600 hover:text-orange-800"
                >
                  <X className="h-3 w-3" />
                </button>
              </span>
            ))}
            
            {filters.search && (
              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                Búsqueda: {filters.search}
                <button
                  onClick={() => handleSearchChange('')}
                  className="ml-1 h-3 w-3 text-green-600 hover:text-green-800"
                >
                  <X className="h-3 w-3" />
                </button>
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default InvestigationFiltersComponent;