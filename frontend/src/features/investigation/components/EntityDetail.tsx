import React, { useState, useEffect } from 'react';
import { ArrowLeft, Edit, Trash2, ExternalLink, Copy, Check, User, Building, Globe, Server, Mail, Phone, MapPin, Calendar, Tag, FileText, Link as LinkIcon, History, RefreshCw } from 'lucide-react';
import Swal from 'sweetalert2';
import type { Entity } from '../../../types';
import { apiService } from '../../../services/api';
import EntityPropertiesPanel from './EntityPropertiesPanel';
import RelationshipManager from './RelationshipManager';

interface EntityDetailProps {
  entityId: string;
  onBack: () => void;
  onEdit: (entity: Entity) => void;
  onDelete: (entityId: string) => void;
}

type TabType = 'overview' | 'properties' | 'relationships' | 'history';

const EntityDetail: React.FC<EntityDetailProps> = ({
  entityId,
  onBack,
  onEdit,
  onDelete
}) => {
  const [entity, setEntity] = useState<Entity | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<TabType>('overview');
  const [copied, setCopied] = useState(false);
  const [relationships, setRelationships] = useState<any[]>([]);
  const [history] = useState<any[]>([]);

  useEffect(() => {
    loadEntity();
  }, [entityId]);

  const loadEntity = async () => {
    try {
      setLoading(true);
      setError(null);
      const entities = await apiService.getEntities();
      if (entities.success && entities.data) {
        const foundEntity = entities.data.find(e => e.id === entityId);
        if (!foundEntity) {
          throw new Error('Entidad no encontrada');
        }

        setEntity(foundEntity);

        const investigationId = foundEntity.investigationId || foundEntity.investigation;
        if (investigationId) {
          const relationshipsResponse = await apiService.getEntityRelationships(entityId, investigationId);
          if (relationshipsResponse.success && relationshipsResponse.data) {
            setRelationships(relationshipsResponse.data);
          } else {
            setRelationships([]);
          }
        } else {
          setRelationships([]);
        }
      } else {
        throw new Error('Error al cargar entidades');
      }
      
    } catch (err) {
      setError('Error al cargar la entidad');
      console.error('Error loading entity:', err);
    } finally {
      setLoading(false);
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

  const getEntityTypeLabel = (type: string) => {
    switch (type) {
      case 'person': return 'Persona';
      case 'organization': return 'Organización';
      case 'domain': return 'Dominio';
      case 'ip': return 'Dirección IP';
      case 'email': return 'Email';
      case 'phone': return 'Teléfono';
      case 'location': return 'Ubicación';
      default: return 'Entidad';
    }
  };

  const copyToClipboard = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Error copying to clipboard:', err);
    }
  };

  const handleDelete = async () => {
    const result = await Swal.fire({
      title: '¿Estás seguro?',
      text: "¿Estás seguro de que quieres eliminar esta entidad?",
      icon: 'warning',
      showCancelButton: true,
      confirmButtonColor: '#d33',
      cancelButtonColor: '#3085d6',
      confirmButtonText: 'Sí, eliminar',
      cancelButtonText: 'Cancelar'
    });

    if (result.isConfirmed) {
      onDelete(entityId);
    }
  };

  const getExternalLink = (type: string, value: string) => {
    switch (type) {
      case 'domain':
        return `https://${value}`;
      case 'email':
        return `mailto:${value}`;
      case 'phone':
        return `tel:${value}`;
      case 'location':
        return `https://maps.google.com/maps?q=${encodeURIComponent(value)}`;
      default:
        return null;
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="w-8 h-8 animate-spin text-blue-600" />
        <span className="ml-2 text-gray-600 dark:text-gray-400">Cargando entidad...</span>
      </div>
    );
  }

  if (error || !entity) {
    return (
      <div className="text-center py-12">
        <div className="text-red-400 mb-4">
          <Tag className="w-12 h-12 mx-auto" />
        </div>
        <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
          Error al cargar la entidad
        </h3>
        <p className="text-gray-600 dark:text-gray-400 mb-4">
          {error || 'La entidad no fue encontrada'}
        </p>
        <button
          onClick={onBack}
          className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
        >
          Volver
        </button>
      </div>
    );
  }

  const IconComponent = getEntityIcon(entity.type);
  const externalLink = entity.value ? getExternalLink(entity.type, entity.value) : null;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm p-6">
        <div className="flex items-center justify-between mb-4">
          <button
            onClick={onBack}
            className="flex items-center space-x-2 text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            <span>Volver</span>
          </button>
          
          <div className="flex items-center space-x-2">
            <button
              onClick={() => onEdit(entity)}
              className="p-2 text-gray-600 dark:text-gray-400 hover:text-blue-600 dark:hover:text-blue-400 transition-colors"
              title="Editar entidad"
            >
              <Edit className="w-4 h-4" />
            </button>
            <button
              onClick={handleDelete}
              className="p-2 text-gray-600 dark:text-gray-400 hover:text-red-600 dark:hover:text-red-400 transition-colors"
              title="Eliminar entidad"
            >
              <Trash2 className="w-4 h-4" />
            </button>
          </div>
        </div>
        
        <div className="flex items-start space-x-4">
          <div className={`p-3 rounded-lg bg-gray-50 dark:bg-gray-700 ${getEntityColor(entity.type)}`}>
            <IconComponent className="w-8 h-8" />
          </div>
          
          <div className="flex-1">
            <div className="flex items-center space-x-2 mb-2">
              <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
                {entity.name}
              </h1>
              <span className={`px-2 py-1 text-xs font-medium rounded-full bg-gray-100 dark:bg-gray-700 ${getEntityColor(entity.type)}`}>
                {getEntityTypeLabel(entity.type)}
              </span>
            </div>
            
            <div className="flex items-center space-x-4 text-sm text-gray-600 dark:text-gray-400">
              <div className="flex items-center space-x-2">
                <span className="font-medium">Valor:</span>
                <code className="px-2 py-1 bg-gray-100 dark:bg-gray-700 rounded text-gray-900 dark:text-white">
                  {entity.value}
                </code>
                <button
                  onClick={() => copyToClipboard(entity.value || '')}
                  className="p-1 hover:text-gray-900 dark:hover:text-white transition-colors"
                  title="Copiar valor"
                >
                  {copied ? <Check className="w-3 h-3 text-green-600" /> : <Copy className="w-3 h-3" />}
                </button>
                {externalLink && (
                  <a
                    href={externalLink}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="p-1 hover:text-blue-600 dark:hover:text-blue-400 transition-colors"
                    title="Abrir enlace externo"
                  >
                    <ExternalLink className="w-3 h-3" />
                  </a>
                )}
              </div>
            </div>
            
            {entity.description && (
              <p className="mt-2 text-gray-700 dark:text-gray-300">
                {entity.description}
              </p>
            )}
            
            <div className="flex items-center space-x-4 mt-3 text-xs text-gray-500 dark:text-gray-400">
              <div className="flex items-center space-x-1">
                <Calendar className="w-3 h-3" />
                <span>Creado: {(entity.created_at || entity.createdAt) ? new Date(entity.created_at || entity.createdAt || '').toLocaleDateString() : 'N/A'}</span>
              </div>
              <div className="flex items-center space-x-1">
                <Calendar className="w-3 h-3" />
                <span>Actualizado: {(entity.updated_at || entity.updatedAt) ? new Date(entity.updated_at || entity.updatedAt || '').toLocaleDateString() : 'N/A'}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm">
        <div className="border-b border-gray-200 dark:border-gray-700">
          <nav className="flex space-x-8 px-6">
            {[
              { id: 'overview', label: 'Resumen', icon: FileText },
              { id: 'properties', label: 'Propiedades', icon: Tag },
              { id: 'relationships', label: 'Relaciones', icon: LinkIcon },
              { id: 'history', label: 'Historial', icon: History }
            ].map((tab) => {
              const TabIcon = tab.icon;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id as TabType)}
                  className={`flex items-center space-x-2 py-4 px-1 border-b-2 font-medium text-sm transition-colors ${
                    activeTab === tab.id
                      ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                      : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 hover:border-gray-300 dark:hover:border-gray-600'
                  }`}
                >
                  <TabIcon className="w-4 h-4" />
                  <span>{tab.label}</span>
                </button>
              );
            })}
          </nav>
        </div>

        <div className="p-6">
          {activeTab === 'overview' && (
            <div className="space-y-6">
              {/* Basic Information */}
              <div>
                <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
                  Información Básica
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="bg-gray-50 dark:bg-gray-700 p-4 rounded-lg">
                    <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">Tipo</dt>
                    <dd className="mt-1 text-sm text-gray-900 dark:text-white">
                      {getEntityTypeLabel(entity.type)}
                    </dd>
                  </div>
                  <div className="bg-gray-50 dark:bg-gray-700 p-4 rounded-lg">
                    <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">Valor</dt>
                    <dd className="mt-1 text-sm text-gray-900 dark:text-white font-mono">
                      {entity.value}
                    </dd>
                  </div>
                  <div className="bg-gray-50 dark:bg-gray-700 p-4 rounded-lg">
                    <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">Fecha de creación</dt>
                    <dd className="mt-1 text-sm text-gray-900 dark:text-white">
                      {(entity.created_at || entity.createdAt) ? new Date(entity.created_at || entity.createdAt || '').toLocaleString() : 'N/A'}
                    </dd>
                  </div>
                  <div className="bg-gray-50 dark:bg-gray-700 p-4 rounded-lg">
                    <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">Última actualización</dt>
                    <dd className="mt-1 text-sm text-gray-900 dark:text-white">
                      {(entity.updated_at || entity.updatedAt) ? new Date(entity.updated_at || entity.updatedAt || '').toLocaleString() : 'N/A'}
                    </dd>
                  </div>
                </div>
              </div>

              {/* Quick Stats */}
              <div>
                <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
                  Estadísticas Rápidas
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="bg-blue-50 dark:bg-blue-900/20 p-4 rounded-lg">
                    <div className="flex items-center">
                      <LinkIcon className="w-5 h-5 text-blue-600 dark:text-blue-400" />
                      <div className="ml-3">
                        <p className="text-sm font-medium text-blue-900 dark:text-blue-100">
                          Relaciones
                        </p>
                        <p className="text-lg font-semibold text-blue-600 dark:text-blue-400">
                          {relationships.length}
                        </p>
                      </div>
                    </div>
                  </div>
                  <div className="bg-green-50 dark:bg-green-900/20 p-4 rounded-lg">
                    <div className="flex items-center">
                      <Tag className="w-5 h-5 text-green-600 dark:text-green-400" />
                      <div className="ml-3">
                        <p className="text-sm font-medium text-green-900 dark:text-green-100">
                          Propiedades
                        </p>
                        <p className="text-lg font-semibold text-green-600 dark:text-green-400">
                          {Object.keys(entity.properties || {}).length}
                        </p>
                      </div>
                    </div>
                  </div>
                  <div className="bg-purple-50 dark:bg-purple-900/20 p-4 rounded-lg">
                    <div className="flex items-center">
                      <History className="w-5 h-5 text-purple-600 dark:text-purple-400" />
                      <div className="ml-3">
                        <p className="text-sm font-medium text-purple-900 dark:text-purple-100">
                          Actividad
                        </p>
                        <p className="text-lg font-semibold text-purple-600 dark:text-purple-400">
                          {history.length}
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'properties' && (
            <EntityPropertiesPanel
              entity={entity}
              onUpdate={(updatedEntity) => setEntity(updatedEntity)}
            />
          )}

          {activeTab === 'relationships' && (
            <RelationshipManager
              entityId={entity.id}
              investigationId={entity.investigationId || entity.investigation}
              relationships={relationships}
              onRelationshipChange={() => {
                // Reload relationships
                const investigationId = entity.investigationId || entity.investigation;
                if (!investigationId) return;
                apiService.getEntityRelationships(entity.id, investigationId)
                  .then(response => {
                    if (response.success && response.data) {
                      setRelationships(response.data);
                    }
                  })
                  .catch(console.error);
              }}
            />
          )}

          {activeTab === 'history' && (
            <div>
              <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
                Historial de Actividad
              </h3>
              {history.length === 0 ? (
                <div className="text-center py-8">
                  <History className="w-12 h-12 text-gray-400 dark:text-gray-600 mx-auto mb-4" />
                  <p className="text-gray-600 dark:text-gray-400">
                    No hay actividad registrada para esta entidad
                  </p>
                </div>
              ) : (
                <div className="space-y-4">
                  {history.map((item: any, index: number) => (
                    <div key={index} className="flex items-start space-x-3 p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
                      <div className="flex-shrink-0">
                        <div className="w-2 h-2 bg-blue-600 rounded-full mt-2"></div>
                      </div>
                      <div className="flex-1">
                        <p className="text-sm text-gray-900 dark:text-white">
                          {item.description}
                        </p>
                        <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                          {new Date(item.timestamp).toLocaleString()}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default EntityDetail;
