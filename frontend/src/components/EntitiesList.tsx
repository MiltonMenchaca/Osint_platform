import React, { useState, useEffect } from 'react';
import { Plus, Search, Filter, Grid, List, RefreshCw } from 'lucide-react';
import type { Entity } from '../types';
import { ApiService } from '../services/api';

const apiService = new ApiService();
import EntityCard from './EntityCard';
import EntityTypeSelector from './EntityTypeSelector';

interface EntitiesListProps {
  investigationId?: string;
  onEntitySelect?: (entity: Entity) => void;
  onEntityCreate?: () => void;
  onEntityEdit?: (entity: Entity) => void;
}

const EntitiesList: React.FC<EntitiesListProps> = ({
  investigationId,
  onEntitySelect,
  onEntityCreate,
  onEntityEdit
}) => {
  const [entities, setEntities] = useState<Entity[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedType, setSelectedType] = useState('');
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  const [showFilters, setShowFilters] = useState(false);
  const [sortBy, setSortBy] = useState<'name' | 'type' | 'created_at'>('created_at');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');

  useEffect(() => {
    loadEntities();
  }, [investigationId]);

  const loadEntities = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const params: any = {};
      if (investigationId) {
        params.investigation = investigationId;
      }
      if (searchTerm) {
        params.search = searchTerm;
      }
      if (selectedType) {
        params.type = selectedType;
      }
      params.ordering = sortOrder === 'desc' ? `-${sortBy}` : sortBy;
      
      const response = await apiService.getEntities(params);
      setEntities(response.data || []);
    } catch (err) {
      setError('Error al cargar las entidades');
      console.error('Error loading entities:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    loadEntities();
  };

  const handleRefresh = () => {
    loadEntities();
  };

  const handleEntityDelete = async (entityId: string) => {
    try {
      await apiService.deleteEntity(entityId);
      setEntities(entities.filter(entity => entity.id !== entityId));
    } catch (err) {
      console.error('Error deleting entity:', err);
    }
  };

  const filteredEntities = entities.filter(entity => {
    const matchesSearch = !searchTerm || 
      entity.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (entity.value && entity.value.toLowerCase().includes(searchTerm.toLowerCase()));
    
    const matchesType = !selectedType || entity.type === selectedType;
    
    return matchesSearch && matchesType;
  });

  const sortedEntities = [...filteredEntities].sort((a, b) => {
    let aValue: any, bValue: any;
    
    switch (sortBy) {
      case 'name':
        aValue = a.name.toLowerCase();
        bValue = b.name.toLowerCase();
        break;
      case 'type':
        aValue = a.type;
        bValue = b.type;
        break;
      case 'created_at':
        aValue = new Date(a.created_at || a.createdAt || '');
        bValue = new Date(b.created_at || b.createdAt || '');
        break;
      default:
        return 0;
    }
    
    if (aValue < bValue) return sortOrder === 'asc' ? -1 : 1;
    if (aValue > bValue) return sortOrder === 'asc' ? 1 : -1;
    return 0;
  });

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="w-8 h-8 animate-spin text-blue-600" />
        <span className="ml-2 text-gray-600 dark:text-gray-400">Cargando entidades...</span>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
            Entidades
            {investigationId && " de la Investigación"}
          </h2>
          <p className="text-gray-600 dark:text-gray-400">
            {sortedEntities.length} entidad{sortedEntities.length !== 1 ? 'es' : ''} encontrada{sortedEntities.length !== 1 ? 's' : ''}
          </p>
        </div>
        
        <div className="flex items-center space-x-2">
          <button
            onClick={handleRefresh}
            className="p-2 text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white transition-colors"
            title="Actualizar"
          >
            <RefreshCw className="w-5 h-5" />
          </button>
          
          <button
            onClick={() => setViewMode(viewMode === 'grid' ? 'list' : 'grid')}
            className="p-2 text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white transition-colors"
            title={`Cambiar a vista ${viewMode === 'grid' ? 'lista' : 'cuadrícula'}`}
          >
            {viewMode === 'grid' ? <List className="w-5 h-5" /> : <Grid className="w-5 h-5" />}
          </button>
          
          <button
            onClick={() => setShowFilters(!showFilters)}
            className={`p-2 transition-colors ${
              showFilters 
                ? 'text-blue-600 dark:text-blue-400' 
                : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
            }`}
            title="Filtros"
          >
            <Filter className="w-5 h-5" />
          </button>
          
          {onEntityCreate && (
            <button
              onClick={onEntityCreate}
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors flex items-center space-x-2"
            >
              <Plus className="w-4 h-4" />
              <span>Nueva Entidad</span>
            </button>
          )}
        </div>
      </div>

      {/* Search and Filters */}
      <div className="space-y-4">
        {/* Search Bar */}
        <form onSubmit={handleSearch} className="flex space-x-2">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
            <input
              type="text"
              placeholder="Buscar entidades por nombre o valor..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
          <button
            type="submit"
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
          >
            Buscar
          </button>
        </form>

        {/* Filters Panel */}
        {showFilters && (
          <div className="bg-gray-50 dark:bg-gray-800 p-4 rounded-lg space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {/* Type Filter */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Tipo de Entidad
                </label>
                <EntityTypeSelector
                  value={selectedType}
                  onChange={setSelectedType}
                  className="w-full"
                />
              </div>
              
              {/* Sort By */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Ordenar por
                </label>
                <select
                  value={sortBy}
                  onChange={(e) => setSortBy(e.target.value as 'name' | 'type' | 'created_at')}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                >
                  <option value="created_at">Fecha de creación</option>
                  <option value="name">Nombre</option>
                  <option value="type">Tipo</option>
                </select>
              </div>
              
              {/* Sort Order */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Orden
                </label>
                <select
                  value={sortOrder}
                  onChange={(e) => setSortOrder(e.target.value as 'asc' | 'desc')}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                >
                  <option value="desc">Descendente</option>
                  <option value="asc">Ascendente</option>
                </select>
              </div>
            </div>
            
            {/* Clear Filters */}
            <div className="flex justify-end">
              <button
                onClick={() => {
                  setSearchTerm('');
                  setSelectedType('');
                  setSortBy('created_at');
                  setSortOrder('desc');
                  loadEntities();
                }}
                className="px-4 py-2 text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white transition-colors"
              >
                Limpiar filtros
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Error Message */}
      {error && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-md p-4">
          <p className="text-red-800 dark:text-red-200">{error}</p>
        </div>
      )}

      {/* Entities Grid/List */}
      {sortedEntities.length === 0 ? (
        <div className="text-center py-12">
          <div className="text-gray-400 dark:text-gray-600 mb-4">
            <Search className="w-12 h-12 mx-auto" />
          </div>
          <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
            No se encontraron entidades
          </h3>
          <p className="text-gray-600 dark:text-gray-400 mb-4">
            {searchTerm || selectedType 
              ? 'Intenta ajustar los filtros de búsqueda'
              : 'Aún no hay entidades creadas'}
          </p>
          {onEntityCreate && (
            <button
              onClick={onEntityCreate}
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
            >
              Crear primera entidad
            </button>
          )}
        </div>
      ) : (
        <div className={viewMode === 'grid' 
          ? 'grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4'
          : 'space-y-2'
        }>
          {sortedEntities.map((entity) => (
            <EntityCard
              key={entity.id}
              entity={entity}
              onClick={() => onEntitySelect?.(entity)}
              onEdit={() => onEntityEdit?.(entity)}
              onDelete={() => handleEntityDelete(entity.id)}
              compact={viewMode === 'list'}
            />
          ))}
        </div>
      )}
    </div>
  );
};

export default EntitiesList;