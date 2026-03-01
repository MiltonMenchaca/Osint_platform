import React, { useState, useEffect } from 'react';
import { Plus, Edit, Trash2, Save, X, Tag, Type, Calendar, Hash, ToggleLeft, ToggleRight, Link as LinkIcon, FileText, AlertCircle } from 'lucide-react';
import Swal from 'sweetalert2';
import type { Entity } from '../../../types';
import { apiService } from '../../../services/api';

interface EntityPropertiesPanelProps {
  entity: Entity;
  onUpdate: (updatedEntity: Entity) => void;
}

interface Property {
  key: string;
  value: any;
  type: 'string' | 'number' | 'boolean' | 'date' | 'url' | 'email' | 'text';
  editable?: boolean;
}

interface EditingProperty {
  key: string;
  value: string;
  type: string;
  isNew?: boolean;
}

const EntityPropertiesPanel: React.FC<EntityPropertiesPanelProps> = ({
  entity,
  onUpdate
}) => {
  const [properties, setProperties] = useState<Property[]>([]);
  const [editingProperty, setEditingProperty] = useState<EditingProperty | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadProperties();
  }, [entity]);

  const loadProperties = () => {
    const entityProperties = entity.properties || {};
    const propertyList: Property[] = [];

    // Add core properties (non-editable)
    propertyList.push(
      { key: 'id', value: entity.id, type: 'string', editable: false },
      { key: 'name', value: entity.name, type: 'string', editable: true },
      { key: 'type', value: entity.type, type: 'string', editable: false },
      { key: 'value', value: entity.value, type: 'string', editable: true },
      { key: 'description', value: entity.description || '', type: 'text', editable: true },
      { key: 'created_at', value: entity.created_at || entity.createdAt, type: 'date', editable: false },
      { key: 'updated_at', value: entity.updated_at || entity.updatedAt, type: 'date', editable: false }
    );

    // Add custom properties
    Object.entries(entityProperties).forEach(([key, value]) => {
      if (!propertyList.find(p => p.key === key)) {
        propertyList.push({
          key,
          value,
          type: inferPropertyType(value),
          editable: true
        });
      }
    });

    setProperties(propertyList);
  };

  const inferPropertyType = (value: any): Property['type'] => {
    if (typeof value === 'boolean') return 'boolean';
    if (typeof value === 'number') return 'number';
    if (typeof value === 'string') {
      if (value.includes('@')) return 'email';
      if (value.startsWith('http://') || value.startsWith('https://')) return 'url';
      if (value.match(/^\d{4}-\d{2}-\d{2}/)) return 'date';
      if (value.length > 100) return 'text';
    }
    return 'string';
  };

  const getPropertyIcon = (type: string) => {
    switch (type) {
      case 'string': return Type;
      case 'number': return Hash;
      case 'boolean': return ToggleLeft;
      case 'date': return Calendar;
      case 'url': return LinkIcon;
      case 'email': return LinkIcon;
      case 'text': return FileText;
      default: return Tag;
    }
  };

  const formatPropertyValue = (property: Property) => {
    if (property.value === null || property.value === undefined) {
      return <span className="text-gray-400 italic">Sin valor</span>;
    }

    switch (property.type) {
      case 'boolean':
        return (
          <div className="flex items-center space-x-2">
            {property.value ? (
              <ToggleRight className="w-4 h-4 text-green-600" />
            ) : (
              <ToggleLeft className="w-4 h-4 text-gray-400" />
            )}
            <span>{property.value ? 'Verdadero' : 'Falso'}</span>
          </div>
        );
      case 'date':
        return new Date(property.value).toLocaleString();
      case 'url':
        return (
          <a
            href={property.value}
            target="_blank"
            rel="noopener noreferrer"
            className="text-blue-600 dark:text-blue-400 hover:underline flex items-center space-x-1"
          >
            <LinkIcon className="w-3 h-3" />
            <span>{property.value}</span>
          </a>
        );
      case 'email':
        return (
          <a
            href={`mailto:${property.value}`}
            className="text-blue-600 dark:text-blue-400 hover:underline"
          >
            {property.value}
          </a>
        );
      case 'text':
        return (
          <div className="max-w-md">
            <p className="text-sm text-gray-700 dark:text-gray-300 line-clamp-3">
              {property.value}
            </p>
          </div>
        );
      default:
        return <span className="font-mono text-sm">{String(property.value)}</span>;
    }
  };

  const getPropertyLabel = (key: string) => {
    const labels: { [key: string]: string } = {
      id: 'ID',
      name: 'Nombre',
      type: 'Tipo',
      value: 'Valor',
      description: 'Descripción',
      created_at: 'Fecha de creación',
      updated_at: 'Última actualización'
    };
    return labels[key] || key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
  };

  const startEditing = (property: Property) => {
    if (!property.editable) return;
    
    setEditingProperty({
      key: property.key,
      value: String(property.value || ''),
      type: property.type,
      isNew: false
    });
  };

  const startAddingProperty = () => {
    setEditingProperty({
      key: '',
      value: '',
      type: 'string',
      isNew: true
    });
  };

  const cancelEditing = () => {
    setEditingProperty(null);
    setError(null);
  };

  const saveProperty = async () => {
    if (!editingProperty) return;

    try {
      setLoading(true);
      setError(null);

      // Validate
      if (!editingProperty.key.trim()) {
        setError('El nombre de la propiedad es requerido');
        return;
      }

      if (editingProperty.isNew && properties.find(p => p.key === editingProperty.key)) {
        setError('Ya existe una propiedad con ese nombre');
        return;
      }

      // Convert value based on type
      let convertedValue: any = editingProperty.value;
      switch (editingProperty.type) {
        case 'number':
          convertedValue = parseFloat(editingProperty.value) || 0;
          break;
        case 'boolean':
          convertedValue = editingProperty.value.toLowerCase() === 'true';
          break;
        case 'date':
          convertedValue = editingProperty.value;
          break;
        default:
          convertedValue = editingProperty.value;
      }

      // Update entity
      const updatedEntity = { ...entity };
      
      if (['name', 'value', 'description'].includes(editingProperty.key)) {
        // Core property
        (updatedEntity as any)[editingProperty.key] = convertedValue;
      } else {
        // Custom property
        updatedEntity.properties = {
          ...updatedEntity.properties,
          [editingProperty.key]: convertedValue
        };
      }

      // Save to backend
      const response = await apiService.updateEntity(entity.id, updatedEntity);
      if (response.success && response.data) {
        onUpdate(response.data);
      } else {
        throw new Error(response.message || 'Error al actualizar la entidad');
      }
      
      setEditingProperty(null);
    } catch (err) {
      setError('Error al guardar la propiedad');
      console.error('Error saving property:', err);
    } finally {
      setLoading(false);
    }
  };

  const deleteProperty = async (key: string) => {
    if (['id', 'name', 'type', 'value', 'created_at', 'updated_at'].includes(key)) {
      setError('No se puede eliminar una propiedad del sistema');
      return;
    }

    const result = await Swal.fire({
      title: '¿Estás seguro?',
      text: "¿Estás seguro de que quieres eliminar esta propiedad?",
      icon: 'warning',
      showCancelButton: true,
      confirmButtonColor: '#d33',
      cancelButtonColor: '#3085d6',
      confirmButtonText: 'Sí, eliminar',
      cancelButtonText: 'Cancelar'
    });

    if (!result.isConfirmed) {
      return;
    }

    try {
      setLoading(true);
      setError(null);

      const updatedEntity = { ...entity };
      const newProperties = { ...updatedEntity.properties };
      delete newProperties[key];
      updatedEntity.properties = newProperties;

      const response = await apiService.updateEntity(entity.id, updatedEntity);
      if (response.success && response.data) {
        onUpdate(response.data);
      } else {
        throw new Error(response.message || 'Error al actualizar la entidad');
      }
    } catch (err) {
      setError('Error al eliminar la propiedad');
      console.error('Error deleting property:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-medium text-gray-900 dark:text-white">
          Propiedades de la Entidad
        </h3>
        <button
          onClick={startAddingProperty}
          disabled={loading || editingProperty !== null}
          className="flex items-center space-x-2 px-3 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          <Plus className="w-4 h-4" />
          <span>Agregar Propiedad</span>
        </button>
      </div>

      {error && (
        <div className="flex items-center space-x-2 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-md">
          <AlertCircle className="w-4 h-4 text-red-600 dark:text-red-400" />
          <span className="text-sm text-red-700 dark:text-red-300">{error}</span>
        </div>
      )}

      <div className="space-y-3">
        {properties.map((property) => {
          const IconComponent = getPropertyIcon(property.type);
          const isEditing = editingProperty?.key === property.key && !editingProperty.isNew;

          return (
            <div
              key={property.key}
              className="flex items-start space-x-4 p-4 bg-gray-50 dark:bg-gray-700 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-600 transition-colors"
            >
              <div className="flex-shrink-0 mt-1">
                <IconComponent className="w-4 h-4 text-gray-500 dark:text-gray-400" />
              </div>
              
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between mb-1">
                  <h4 className="text-sm font-medium text-gray-900 dark:text-white">
                    {getPropertyLabel(property.key)}
                  </h4>
                  <div className="flex items-center space-x-1">
                    <span className="px-2 py-1 text-xs bg-gray-200 dark:bg-gray-600 text-gray-700 dark:text-gray-300 rounded">
                      {property.type}
                    </span>
                    {property.editable && (
                      <>
                        <button
                          onClick={() => startEditing(property)}
                          disabled={loading || editingProperty !== null}
                          className="p-1 text-gray-500 dark:text-gray-400 hover:text-blue-600 dark:hover:text-blue-400 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                          title="Editar propiedad"
                        >
                          <Edit className="w-3 h-3" />
                        </button>
                        {!['id', 'name', 'type', 'value', 'created_at', 'updated_at'].includes(property.key) && (
                          <button
                            onClick={() => deleteProperty(property.key)}
                            disabled={loading || editingProperty !== null}
                            className="p-1 text-gray-500 dark:text-gray-400 hover:text-red-600 dark:hover:text-red-400 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                            title="Eliminar propiedad"
                          >
                            <Trash2 className="w-3 h-3" />
                          </button>
                        )}
                      </>
                    )}
                  </div>
                </div>
                
                {isEditing ? (
                  <div className="space-y-2">
                    <div className="flex items-center space-x-2">
                      <select
                        value={editingProperty.type}
                        onChange={(e) => setEditingProperty({ ...editingProperty, type: e.target.value })}
                        className="px-2 py-1 text-xs border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
                      >
                        <option value="string">Texto</option>
                        <option value="number">Número</option>
                        <option value="boolean">Booleano</option>
                        <option value="date">Fecha</option>
                        <option value="url">URL</option>
                        <option value="email">Email</option>
                        <option value="text">Texto largo</option>
                      </select>
                    </div>
                    
                    {editingProperty.type === 'boolean' ? (
                      <select
                        value={editingProperty.value}
                        onChange={(e) => setEditingProperty({ ...editingProperty, value: e.target.value })}
                        className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      >
                        <option value="true">Verdadero</option>
                        <option value="false">Falso</option>
                      </select>
                    ) : editingProperty.type === 'text' ? (
                      <textarea
                        value={editingProperty.value}
                        onChange={(e) => setEditingProperty({ ...editingProperty, value: e.target.value })}
                        rows={3}
                        className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                        placeholder="Ingresa el valor de la propiedad"
                      />
                    ) : (
                      <input
                        type={editingProperty.type === 'number' ? 'number' : editingProperty.type === 'date' ? 'datetime-local' : 'text'}
                        value={editingProperty.value}
                        onChange={(e) => setEditingProperty({ ...editingProperty, value: e.target.value })}
                        className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                        placeholder="Ingresa el valor de la propiedad"
                      />
                    )}
                    
                    <div className="flex items-center space-x-2">
                      <button
                        onClick={saveProperty}
                        disabled={loading}
                        className="flex items-center space-x-1 px-3 py-1 bg-green-600 text-white rounded text-sm hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                      >
                        <Save className="w-3 h-3" />
                        <span>Guardar</span>
                      </button>
                      <button
                        onClick={cancelEditing}
                        disabled={loading}
                        className="flex items-center space-x-1 px-3 py-1 bg-gray-600 text-white rounded text-sm hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                      >
                        <X className="w-3 h-3" />
                        <span>Cancelar</span>
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="text-sm text-gray-700 dark:text-gray-300">
                    {formatPropertyValue(property)}
                  </div>
                )}
              </div>
            </div>
          );
        })}

        {/* Add new property form */}
        {editingProperty?.isNew && (
          <div className="p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
            <h4 className="text-sm font-medium text-blue-900 dark:text-blue-100 mb-3">
              Nueva Propiedad
            </h4>
            
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-blue-800 dark:text-blue-200 mb-1">
                  Nombre de la propiedad
                </label>
                <input
                  type="text"
                  value={editingProperty.key}
                  onChange={(e) => setEditingProperty({ ...editingProperty, key: e.target.value })}
                  className="w-full px-3 py-2 border border-blue-300 dark:border-blue-600 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="ej: telefono_secundario"
                />
              </div>
              
              <div>
                <label className="block text-xs font-medium text-blue-800 dark:text-blue-200 mb-1">
                  Tipo de dato
                </label>
                <select
                  value={editingProperty.type}
                  onChange={(e) => setEditingProperty({ ...editingProperty, type: e.target.value })}
                  className="w-full px-3 py-2 border border-blue-300 dark:border-blue-600 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  <option value="string">Texto</option>
                  <option value="number">Número</option>
                  <option value="boolean">Booleano</option>
                  <option value="date">Fecha</option>
                  <option value="url">URL</option>
                  <option value="email">Email</option>
                  <option value="text">Texto largo</option>
                </select>
              </div>
              
              <div>
                <label className="block text-xs font-medium text-blue-800 dark:text-blue-200 mb-1">
                  Valor
                </label>
                {editingProperty.type === 'boolean' ? (
                  <select
                    value={editingProperty.value}
                    onChange={(e) => setEditingProperty({ ...editingProperty, value: e.target.value })}
                    className="w-full px-3 py-2 border border-blue-300 dark:border-blue-600 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  >
                    <option value="true">Verdadero</option>
                    <option value="false">Falso</option>
                  </select>
                ) : editingProperty.type === 'text' ? (
                  <textarea
                    value={editingProperty.value}
                    onChange={(e) => setEditingProperty({ ...editingProperty, value: e.target.value })}
                    rows={3}
                    className="w-full px-3 py-2 border border-blue-300 dark:border-blue-600 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    placeholder="Ingresa el valor de la propiedad"
                  />
                ) : (
                  <input
                    type={editingProperty.type === 'number' ? 'number' : editingProperty.type === 'date' ? 'datetime-local' : 'text'}
                    value={editingProperty.value}
                    onChange={(e) => setEditingProperty({ ...editingProperty, value: e.target.value })}
                    className="w-full px-3 py-2 border border-blue-300 dark:border-blue-600 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    placeholder="Ingresa el valor de la propiedad"
                  />
                )}
              </div>
              
              <div className="flex items-center space-x-2">
                <button
                  onClick={saveProperty}
                  disabled={loading || !editingProperty.key.trim()}
                  className="flex items-center space-x-1 px-3 py-2 bg-blue-600 text-white rounded text-sm hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  <Save className="w-3 h-3" />
                  <span>Agregar Propiedad</span>
                </button>
                <button
                  onClick={cancelEditing}
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
      </div>

      {properties.length === 0 && (
        <div className="text-center py-8">
          <Tag className="w-12 h-12 text-gray-400 dark:text-gray-600 mx-auto mb-4" />
          <p className="text-gray-600 dark:text-gray-400">
            No hay propiedades definidas para esta entidad
          </p>
        </div>
      )}
    </div>
  );
};

export default EntityPropertiesPanel;