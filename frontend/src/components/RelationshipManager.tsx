import React, { useState, useEffect } from 'react';
import { Plus, Trash2, Save, X, Link as LinkIcon, ArrowRight, Search, Filter, User, Building, Globe, Server, Mail, Phone, MapPin, Tag, AlertCircle } from 'lucide-react';
import type { Entity } from '../types';
import { apiService } from '../services/api';

interface Relationship {
  id: string;
  source_entity_id: string;
  target_entity_id: string;
  relationship_type: string;
  properties?: { [key: string]: any };
  created_at: string;
  source_entity?: Entity;
  target_entity?: Entity;
}

interface RelationshipManagerProps {
  entityId: string;
  relationships: Relationship[];
  onRelationshipChange: () => void;
}

interface NewRelationship {
  target_entity_id: string;
  relationship_type: string;
  properties: { [key: string]: any };
}

const RELATIONSHIP_TYPES = [
  { value: 'connected_to', label: 'Conectado a', description: 'Conexión general' },
  { value: 'owns', label: 'Posee', description: 'Relación de propiedad' },
  { value: 'works_for', label: 'Trabaja para', description: 'Relación laboral' },
  { value: 'lives_at', label: 'Vive en', description: 'Relación de residencia' },
  { value: 'communicates_with', label: 'Se comunica con', description: 'Relación de comunicación' },
  { value: 'related_to', label: 'Relacionado con', description: 'Relación familiar' },
  { value: 'member_of', label: 'Miembro de', description: 'Pertenencia a organización' },
  { value: 'located_at', label: 'Ubicado en', description: 'Relación de ubicación' },
  { value: 'registered_to', label: 'Registrado a', description: 'Relación de registro' },
  { value: 'associated_with', label: 'Asociado con', description: 'Asociación general' }
];

const RelationshipManager: React.FC<RelationshipManagerProps> = ({
  entityId,
  relationships,
  onRelationshipChange
}) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showAddForm, setShowAddForm] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterType, setFilterType] = useState('');
  const [availableEntities, setAvailableEntities] = useState<Entity[]>([]);
  const [newRelationship, setNewRelationship] = useState<NewRelationship>({
    target_entity_id: '',
    relationship_type: '',
    properties: {}
  });

  useEffect(() => {
    loadAvailableEntities();
  }, []);

  const loadAvailableEntities = async () => {
    try {
      const response = await apiService.getEntities();
      if (response.success && response.data) {
        // Filter out the current entity
        setAvailableEntities(response.data.filter(e => e.id !== entityId));
      }
    } catch (err) {
      console.error('Error loading entities:', err);
    }
  };

  const getEntityIcon = (type: string) => {
    switch (type) {
      case 'person': return User;
      case 'organization': return Building;
      case 'domain': return Globe;
      case 'ip': return Server;
      case 'email': return Mail;
      case 'phone': return Phone;
      case 'location': return MapPin;
      default: return Tag;
    }
  };

  const getEntityColor = (type: string) => {
    switch (type) {
      case 'person': return 'text-blue-600 dark:text-blue-400';
      case 'organization': return 'text-green-600 dark:text-green-400';
      case 'domain': return 'text-purple-600 dark:text-purple-400';
      case 'ip': return 'text-red-600 dark:text-red-400';
      case 'email': return 'text-yellow-600 dark:text-yellow-400';
      case 'phone': return 'text-indigo-600 dark:text-indigo-400';
      case 'location': return 'text-pink-600 dark:text-pink-400';
      default: return 'text-gray-600 dark:text-gray-400';
    }
  };

  const getRelationshipTypeLabel = (type: string) => {
    const relationshipType = RELATIONSHIP_TYPES.find(rt => rt.value === type);
    return relationshipType ? relationshipType.label : type;
  };

  const getRelationshipColor = (type: string) => {
    const colors: { [key: string]: string } = {
      connected_to: 'bg-blue-100 text-blue-800 dark:bg-blue-900/20 dark:text-blue-300',
      owns: 'bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-300',
      works_for: 'bg-purple-100 text-purple-800 dark:bg-purple-900/20 dark:text-purple-300',
      lives_at: 'bg-pink-100 text-pink-800 dark:bg-pink-900/20 dark:text-pink-300',
      communicates_with: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/20 dark:text-yellow-300',
      related_to: 'bg-red-100 text-red-800 dark:bg-red-900/20 dark:text-red-300',
      member_of: 'bg-indigo-100 text-indigo-800 dark:bg-indigo-900/20 dark:text-indigo-300',
      located_at: 'bg-teal-100 text-teal-800 dark:bg-teal-900/20 dark:text-teal-300',
      registered_to: 'bg-orange-100 text-orange-800 dark:bg-orange-900/20 dark:text-orange-300',
      associated_with: 'bg-gray-100 text-gray-800 dark:bg-gray-900/20 dark:text-gray-300'
    };
    return colors[type] || 'bg-gray-100 text-gray-800 dark:bg-gray-900/20 dark:text-gray-300';
  };

  const filteredRelationships = relationships.filter(rel => {
    const matchesSearch = !searchTerm || 
      (rel.source_entity?.name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
       rel.target_entity?.name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
       rel.relationship_type.toLowerCase().includes(searchTerm.toLowerCase()));
    
    const matchesFilter = !filterType || rel.relationship_type === filterType;
    
    return matchesSearch && matchesFilter;
  });

  const handleAddRelationship = async () => {
    if (!newRelationship.target_entity_id || !newRelationship.relationship_type) {
      setError('Por favor selecciona una entidad y un tipo de relación');
      return;
    }

    try {
      setLoading(true);
      setError(null);

      const response = await apiService.createEntityRelationship(
        entityId,
        newRelationship.target_entity_id,
        newRelationship.relationship_type
      );
      
      if (!response.success) {
        throw new Error(response.message || 'Error al crear la relación');
      }

      setNewRelationship({
        target_entity_id: '',
        relationship_type: '',
        properties: {}
      });
      setShowAddForm(false);
      onRelationshipChange();
    } catch (err) {
      setError('Error al crear la relación');
      console.error('Error creating relationship:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteRelationship = async (relationshipId: string) => {
    if (!window.confirm('¿Estás seguro de que quieres eliminar esta relación?')) {
      return;
    }

    try {
      setLoading(true);
      setError(null);

      const response = await apiService.deleteEntityRelationship(relationshipId);
      if (!response.success) {
        throw new Error(response.message || 'Error al eliminar la relación');
      }
      
      onRelationshipChange();
    } catch (err) {
      setError('Error al eliminar la relación');
      console.error('Error deleting relationship:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-medium text-gray-900 dark:text-white">
          Relaciones de la Entidad
        </h3>
        <button
          onClick={() => setShowAddForm(!showAddForm)}
          disabled={loading}
          className="flex items-center space-x-2 px-3 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          <Plus className="w-4 h-4" />
          <span>Agregar Relación</span>
        </button>
      </div>

      {error && (
        <div className="flex items-center space-x-2 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-md">
          <AlertCircle className="w-4 h-4 text-red-600 dark:text-red-400" />
          <span className="text-sm text-red-700 dark:text-red-300">{error}</span>
        </div>
      )}

      {/* Add Relationship Form */}
      {showAddForm && (
        <div className="p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
          <h4 className="text-sm font-medium text-blue-900 dark:text-blue-100 mb-4">
            Nueva Relación
          </h4>
          
          <div className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-blue-800 dark:text-blue-200 mb-2">
                Entidad de destino
              </label>
              <select
                value={newRelationship.target_entity_id}
                onChange={(e) => setNewRelationship({ ...newRelationship, target_entity_id: e.target.value })}
                className="w-full px-3 py-2 border border-blue-300 dark:border-blue-600 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value="">Selecciona una entidad</option>
                {availableEntities.map((entity) => (
                    <option key={entity.id} value={entity.id}>
                      {entity.name} ({entity.type}) - {entity.value || ''}
                    </option>
                  ))}
              </select>
            </div>
            
            <div>
              <label className="block text-xs font-medium text-blue-800 dark:text-blue-200 mb-2">
                Tipo de relación
              </label>
              <select
                value={newRelationship.relationship_type}
                onChange={(e) => setNewRelationship({ ...newRelationship, relationship_type: e.target.value })}
                className="w-full px-3 py-2 border border-blue-300 dark:border-blue-600 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value="">Selecciona un tipo de relación</option>
                {RELATIONSHIP_TYPES.map((type) => (
                  <option key={type.value} value={type.value}>
                    {type.label} - {type.description}
                  </option>
                ))}
              </select>
            </div>
            
            <div className="flex items-center space-x-2">
              <button
                onClick={handleAddRelationship}
                disabled={loading || !newRelationship.target_entity_id || !newRelationship.relationship_type}
                className="flex items-center space-x-1 px-3 py-2 bg-blue-600 text-white rounded text-sm hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                <Save className="w-3 h-3" />
                <span>Crear Relación</span>
              </button>
              <button
                onClick={() => {
                  setShowAddForm(false);
                  setNewRelationship({ target_entity_id: '', relationship_type: '', properties: {} });
                  setError(null);
                }}
                disabled={loading}
                className="flex items-center space-x-1 px-3 py-2 bg-gray-600 text-white rounded text-sm hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                <X className="w-3 h-3" />
                <span>Cancelar</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="flex items-center space-x-4">
        <div className="flex-1">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              placeholder="Buscar relaciones..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
        </div>
        
        <div className="flex items-center space-x-2">
          <Filter className="w-4 h-4 text-gray-500 dark:text-gray-400" />
          <select
            value={filterType}
            onChange={(e) => setFilterType(e.target.value)}
            className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value="">Todos los tipos</option>
            {RELATIONSHIP_TYPES.map((type) => (
              <option key={type.value} value={type.value}>
                {type.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Relationships List */}
      <div className="space-y-3">
        {filteredRelationships.length === 0 ? (
          <div className="text-center py-8">
            <LinkIcon className="w-12 h-12 text-gray-400 dark:text-gray-600 mx-auto mb-4" />
            <p className="text-gray-600 dark:text-gray-400">
              {relationships.length === 0 
                ? 'No hay relaciones definidas para esta entidad'
                : 'No se encontraron relaciones que coincidan con los filtros'
              }
            </p>
          </div>
        ) : (
          filteredRelationships.map((relationship) => {
            // Determine which entity is the "other" entity
            const isSource = relationship.source_entity_id === entityId;
            const otherEntity = isSource ? relationship.target_entity : relationship.source_entity;
            
            if (!otherEntity) return null;
            
            const OtherEntityIcon = getEntityIcon(otherEntity.type);
            
            return (
              <div
                key={relationship.id}
                className="flex items-center space-x-4 p-4 bg-gray-50 dark:bg-gray-700 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-600 transition-colors"
              >
                <div className="flex items-center space-x-3 flex-1">
                  {/* Relationship Direction */}
                  <div className="flex items-center space-x-2">
                    <div className={`p-2 rounded-lg bg-white dark:bg-gray-800 ${getEntityColor(otherEntity.type)}`}>
                      <OtherEntityIcon className="w-4 h-4" />
                    </div>
                    <ArrowRight className="w-4 h-4 text-gray-400" />
                  </div>
                  
                  {/* Entity Info */}
                  <div className="flex-1">
                    <div className="flex items-center space-x-2 mb-1">
                      <h4 className="text-sm font-medium text-gray-900 dark:text-white">
                        {otherEntity.name}
                      </h4>
                      <span className={`px-2 py-1 text-xs rounded-full ${getRelationshipColor(relationship.relationship_type)}`}>
                        {getRelationshipTypeLabel(relationship.relationship_type)}
                      </span>
                    </div>
                    <div className="flex items-center space-x-4 text-xs text-gray-500 dark:text-gray-400">
                      <span>{otherEntity.type}</span>
                      <span>•</span>
                      <span>{otherEntity.value}</span>
                      <span>•</span>
                      <span>Creado: {relationship.created_at ? new Date(relationship.created_at).toLocaleDateString() : 'N/A'}</span>
                    </div>
                  </div>
                </div>
                
                {/* Actions */}
                <div className="flex items-center space-x-1">
                  <button
                    onClick={() => handleDeleteRelationship(relationship.id)}
                    disabled={loading}
                    className="p-2 text-gray-500 dark:text-gray-400 hover:text-red-600 dark:hover:text-red-400 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    title="Eliminar relación"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Summary */}
      {relationships.length > 0 && (
        <div className="bg-gray-50 dark:bg-gray-700 p-4 rounded-lg">
          <h4 className="text-sm font-medium text-gray-900 dark:text-white mb-2">
            Resumen de Relaciones
          </h4>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            <div>
              <span className="text-gray-500 dark:text-gray-400">Total:</span>
              <span className="ml-2 font-medium text-gray-900 dark:text-white">
                {relationships.length}
              </span>
            </div>
            <div>
              <span className="text-gray-500 dark:text-gray-400">Tipos únicos:</span>
              <span className="ml-2 font-medium text-gray-900 dark:text-white">
                {new Set(relationships.map(r => r.relationship_type)).size}
              </span>
            </div>
            <div>
              <span className="text-gray-500 dark:text-gray-400">Entidades conectadas:</span>
              <span className="ml-2 font-medium text-gray-900 dark:text-white">
                {new Set(relationships.map(r => 
                  r.source_entity_id === entityId ? r.target_entity_id : r.source_entity_id
                )).size}
              </span>
            </div>
            <div>
              <span className="text-gray-500 dark:text-gray-400">Filtradas:</span>
              <span className="ml-2 font-medium text-gray-900 dark:text-white">
                {filteredRelationships.length}
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default RelationshipManager;