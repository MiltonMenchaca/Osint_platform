import React, { useState, useEffect } from 'react';
import { X, AlertCircle, Plus, Save } from 'lucide-react';
import type { Entity, ValidationErrors } from '../types';
import { apiService } from '../services/api';
import EntityTypeSelector, { EntityTypeGrid } from './EntityTypeSelector';

interface EntityFormProps {
  entity?: Entity;
  investigationId?: string;
  onSave: (entity: Entity) => void;
  onCancel: () => void;
  mode?: 'create' | 'edit';
}

interface FormData {
  name: string;
  type: string;
  value: string;
  description: string;
  properties: { [key: string]: any };
  investigation?: string;
}

// ValidationErrors ya está definido en types/index.ts

const EntityForm: React.FC<EntityFormProps> = ({
  entity,
  investigationId,
  onSave,
  onCancel,
  mode = 'create'
}) => {
  const [formData, setFormData] = useState<FormData>({
    name: '',
    type: '',
    value: '',
    description: '',
    properties: {},
    investigation: investigationId
  });
  
  const [errors, setErrors] = useState<ValidationErrors>({});
  const [loading, setLoading] = useState(false);
  const [customProperties, setCustomProperties] = useState<Array<{key: string, value: string, type: string}>>([]);
  const [useGridSelector, setUseGridSelector] = useState(false);

  useEffect(() => {
    if (entity && mode === 'edit') {
      setFormData({
        name: entity.name || '',
        type: entity.type || '',
        value: entity.value || '',
        description: entity.description || '',
        properties: entity.properties || {},
        investigation: entity.investigation
      });
      
      // Convert properties to custom properties array
      const props = Object.entries(entity.properties || {}).map(([key, value]) => ({
        key,
        value: String(value),
        type: typeof value === 'number' ? 'number' : typeof value === 'boolean' ? 'boolean' : 'text'
      }));
      setCustomProperties(props);
    }
  }, [entity, mode]);

  const validateForm = (): boolean => {
    const newErrors: ValidationErrors = {};
    
    if (!formData.name.trim()) {
      newErrors.name = 'El nombre es requerido';
    }
    
    if (!formData.type) {
      newErrors.type = 'El tipo de entidad es requerido';
    }
    
    if (!formData.value.trim()) {
      newErrors.value = 'El valor es requerido';
    }
    
    // Validate email format if type is email
    if (formData.type === 'email' && formData.value) {
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      if (!emailRegex.test(formData.value)) {
        newErrors.value = 'Formato de email inválido';
      }
    }
    
    // Validate IP format if type is ip
    if (formData.type === 'ip' && formData.value) {
      const ipRegex = /^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$/;
      if (!ipRegex.test(formData.value)) {
        newErrors.value = 'Formato de IP inválido';
      }
    }
    
    // Validate domain format if type is domain
    if (formData.type === 'domain' && formData.value) {
      const domainRegex = /^[a-zA-Z0-9][a-zA-Z0-9-]{1,61}[a-zA-Z0-9]\.[a-zA-Z]{2,}$/;
      if (!domainRegex.test(formData.value)) {
        newErrors.value = 'Formato de dominio inválido';
      }
    }
    
    // Validate phone format if type is phone
    if (formData.type === 'phone' && formData.value) {
      const phoneRegex = /^[+]?[1-9][\d]{0,15}$/;
      if (!phoneRegex.test(formData.value.replace(/[\s\-()]/g, ''))) {
        newErrors.value = 'Formato de teléfono inválido';
      }
    }
    
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!validateForm()) {
      return;
    }
    
    setLoading(true);
    
    try {
      // Convert custom properties back to object
      const properties: { [key: string]: any } = {};
      customProperties.forEach(prop => {
        if (prop.key && prop.value) {
          switch (prop.type) {
            case 'number':
              properties[prop.key] = Number(prop.value);
              break;
            case 'boolean':
              properties[prop.key] = prop.value === 'true';
              break;
            default:
              properties[prop.key] = prop.value;
          }
        }
      });
      
      const entityData: Partial<Entity> = {
        ...formData,
        type: formData.type as Entity['type'],
        properties
      };
      
      let savedEntity: Entity;
      
      let response;
      if (mode === 'edit' && entity) {
        response = await apiService.updateEntity(entity.id, entityData);
      } else {
        response = await apiService.createEntity(entityData);
      }
      
      if (response.success && response.data) {
        savedEntity = response.data;
      } else {
        throw new Error(response.message || 'Error al guardar la entidad');
      }
      
      onSave(savedEntity);
    } catch (error) {
      console.error('Error saving entity:', error);
      setErrors({ name: 'Error al guardar la entidad' });
    } finally {
      setLoading(false);
    }
  };

  const addCustomProperty = () => {
    setCustomProperties([...customProperties, { key: '', value: '', type: 'text' }]);
  };

  const removeCustomProperty = (index: number) => {
    setCustomProperties(customProperties.filter((_, i) => i !== index));
  };

  const updateCustomProperty = (index: number, field: 'key' | 'value' | 'type', value: string) => {
    const updated = [...customProperties];
    updated[index][field] = value;
    setCustomProperties(updated);
  };

  const getPlaceholderForType = (type: string): string => {
    switch (type) {
      case 'person': return 'Ej: Juan Pérez';
      case 'organization': return 'Ej: Empresa ABC S.A.';
      case 'email': return 'Ej: usuario@ejemplo.com';
      case 'phone': return 'Ej: +1234567890';
      case 'ip': return 'Ej: 192.168.1.1';
      case 'domain': return 'Ej: ejemplo.com';
      case 'location': return 'Ej: Madrid, España';
      default: return 'Ingrese el valor';
    }
  };

  return (
    <div className="modal fade show d-block" style={{backgroundColor: 'rgba(0,0,0,0.5)'}}>
      <div className="modal-dialog modal-lg">
        <div className="modal-content">
          <div className="modal-header">
            <h5 className="modal-title">
              {entity ? 'Editar Entidad' : 'Agregar Nueva Entidad'}
            </h5>
            <button
              type="button"
              className="btn-close"
              onClick={onCancel}
              aria-label="Close"
            >
            </button>
          </div>

          <div className="modal-body">
            {errors.name && (
              <div className="alert alert-danger d-flex align-items-center mb-3" role="alert">
                <AlertCircle className="me-2" size={20} />
                <div>{errors.name}</div>
              </div>
            )}
            <form id="entityForm" onSubmit={handleSubmit}>
              <div className="mb-3">
                <label className="form-label fw-medium">
                  Tipo de Entidad
                </label>
                {useGridSelector ? (
                  <EntityTypeGrid
                    value={formData.type}
                    onChange={(type) => setFormData(prev => ({ ...prev, type }))}
                    onTypeSelect={(type) => setFormData(prev => ({ ...prev, type }))}
                  />
                ) : (
                  <EntityTypeSelector
                    value={formData.type}
                    onChange={(type) => setFormData(prev => ({ ...prev, type }))}
                  />
                )}
                <button
                  type="button"
                  onClick={() => setUseGridSelector(!useGridSelector)}
                  className="btn btn-link btn-sm p-0 mt-2"
                >
                  {useGridSelector ? 'Usar selector desplegable' : 'Usar selector visual'}
                </button>
              </div>

              <div className="mb-3">
                <label htmlFor="name" className="form-label fw-medium">
                  Nombre descriptivo de la entidad
                </label>
                <input
                  type="text"
                  id="name"
                  className={`form-control ${
                    errors.name ? 'is-invalid' : ''
                  }`}
                  value={formData.name}
                  onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
                  placeholder="Ej: Servidor principal, Usuario sospechoso, etc."
                />
                {errors.name && (
                  <div className="invalid-feedback">{errors.name}</div>
                )}
              </div>

              <div className="mb-3">
                <label htmlFor="value" className="form-label fw-medium">
                  Valor
                </label>
                <input
                  type="text"
                  id="value"
                  className={`form-control ${
                    errors.value ? 'is-invalid' : ''
                  }`}
                  value={formData.value}
                  onChange={(e) => setFormData(prev => ({ ...prev, value: e.target.value }))}
                  placeholder={getPlaceholderForType(formData.type)}
                />
                {errors.value && (
                  <div className="invalid-feedback">{errors.value}</div>
                )}
              </div>

              <div className="mb-3">
                <label htmlFor="description" className="form-label fw-medium">
                  Descripción (opcional)
                </label>
                <textarea
                  id="description"
                  className="form-control"
                  rows={3}
                  value={formData.description}
                  onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
                  placeholder="Descripción opcional de la entidad"
                />
              </div>

              {/* Custom Properties */}
              <div className="mb-3">
                <div className="d-flex justify-content-between align-items-center mb-3">
                  <label className="form-label fw-medium">
                    Propiedades Personalizadas
                  </label>
                  <button
                    type="button"
                    onClick={addCustomProperty}
                    className="btn btn-outline-primary btn-sm"
                  >
                    <Plus className="me-2" size={16} />
                    Agregar propiedad
                  </button>
                </div>
                
                {customProperties.length > 0 && (
                  <div className="d-flex flex-column gap-2">
                    {customProperties.map((prop, index) => (
                      <div key={index} className="d-flex gap-2 align-items-center">
                        <input
                          type="text"
                          placeholder="Clave"
                          value={prop.key}
                          onChange={(e) => updateCustomProperty(index, 'key', e.target.value)}
                          className="form-control"
                        />
                        <select
                          value={prop.type}
                          onChange={(e) => updateCustomProperty(index, 'type', e.target.value)}
                          className="form-select"
                        >
                          <option value="text">Texto</option>
                          <option value="number">Número</option>
                          <option value="boolean">Booleano</option>
                        </select>
                        {prop.type === 'boolean' ? (
                          <select
                            value={prop.value}
                            onChange={(e) => updateCustomProperty(index, 'value', e.target.value)}
                            className="form-select"
                          >
                            <option value="">Seleccionar...</option>
                            <option value="true">Verdadero</option>
                            <option value="false">Falso</option>
                          </select>
                        ) : (
                          <input
                            type={prop.type === 'number' ? 'number' : 'text'}
                            placeholder="Valor"
                            value={prop.value}
                            onChange={(e) => updateCustomProperty(index, 'value', e.target.value)}
                            className="form-control"
                          />
                        )}
                        <button
                          type="button"
                          onClick={() => removeCustomProperty(index)}
                          className="btn btn-outline-danger btn-sm"
                        >
                          <X size={16} />
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>

            </form>
          </div>
          <div className="modal-footer">
            <button
               type="button"
               onClick={onCancel}
               disabled={loading}
               className="btn btn-secondary"
             >
               Cancelar
             </button>
            <button
              type="submit"
              form="entityForm"
              disabled={loading}
              className="btn btn-primary"
            >
              {loading ? (
                <>
                  <div className="spinner-border spinner-border-sm me-2" role="status">
                    <span className="visually-hidden">Loading...</span>
                  </div>
                  Guardando...
                </>
              ) : (
                <>
                  <Save className="me-2" size={16} />
                  {entity ? 'Actualizar' : 'Crear'} Entidad
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default EntityForm;
