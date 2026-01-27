import React, { useState, useEffect } from 'react';
import type { Investigation, Entity } from '../types';
import {
  ArrowLeft,
  Share,
  Edit,
  Trash2,
  Clock,
  Calendar,
  FileText,
  User,
  Tag,
  Eye,
  Link,
  AlertTriangle
} from 'lucide-react';

interface InvestigationDetailProps {
  investigation: Investigation;
  onBack: () => void;
  onEdit: (investigation: Investigation) => void;
  onDelete: (investigationId: string) => void;
  className?: string;
}

type TabType = 'overview' | 'entities' | 'relationships' | 'history' | 'notes';

interface ActivityItem {
  id: string;
  type: 'created' | 'updated' | 'entity_added' | 'entity_removed' | 'status_changed' | 'note_added';
  description: string;
  timestamp: string;
  user?: string;
  details?: any;
}

const InvestigationDetail: React.FC<InvestigationDetailProps> = ({
  investigation,
  onBack,
  onEdit,
  onDelete,
  className = ''
}) => {
  const [activeTab, setActiveTab] = useState<TabType>('overview');
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [entities, setEntities] = useState<Entity[]>([]);
  const [activity, setActivity] = useState<ActivityItem[]>([]);
  const [loading, setLoading] = useState(false);

  // Mock data - In real app, this would come from API
  useEffect(() => {
    // Simulate loading entities and activity
    setLoading(true);
    setTimeout(() => {
      setEntities(investigation.entities || []);
      setActivity([
        {
          id: '1',
          type: 'created',
          description: 'Investigación creada',
          timestamp: investigation.createdAt,
          user: 'Usuario Actual'
        },
        {
          id: '2',
          type: 'entity_added',
          description: 'Entidad "Persona de Interés" agregada',
          timestamp: new Date(Date.now() - 86400000).toISOString(),
          user: 'Usuario Actual'
        },
        {
          id: '3',
          type: 'status_changed',
          description: `Estado cambiado a "${investigation.status}"`,
          timestamp: new Date(Date.now() - 43200000).toISOString(),
          user: 'Usuario Actual'
        }
      ]);
      setLoading(false);
    }, 500);
  }, [investigation]);

  const getStatusColor = (status: Investigation['status']) => {
    switch (status) {
      case 'active': return 'bg-green-100 text-green-800 border-green-200';
      case 'completed': return 'bg-blue-100 text-blue-800 border-blue-200';
      case 'archived': return 'bg-gray-100 text-gray-800 border-gray-200';
      default: return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  const getPriorityColor = (priority: Investigation['priority']) => {
    switch (priority) {
      case 'critical': return 'bg-red-100 text-red-800 border-red-200';
      case 'high': return 'bg-orange-100 text-orange-800 border-orange-200';
      case 'medium': return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      case 'low': return 'bg-green-100 text-green-800 border-green-200';
      default: return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  const getEntityTypeIcon = (type: Entity['type']) => {
    switch (type) {
      case 'person': return '👤';
      case 'organization': return '🏢';
      case 'location': return '📍';
      case 'phone': return '📞';
      case 'email': return '📧';
      case 'ip': return '🌐';
      case 'domain': return '🔗';
      // case 'document': return '📄'; // 'document' is not a valid entity type
      default: return '❓';
    }
  };

  const getActivityIcon = (type: ActivityItem['type']) => {
    switch (type) {
      case 'created': return <FileText className="h-4 w-4" />;
      case 'updated': return <Edit className="h-4 w-4" />;
      case 'entity_added': return <User className="h-4 w-4" />;
      case 'entity_removed': return <Trash2 className="h-4 w-4" />;
      case 'status_changed': return <Tag className="h-4 w-4" />;
      case 'note_added': return <FileText className="h-4 w-4" />;
      default: return <Clock className="h-4 w-4" />;
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('es-ES', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const handleDelete = () => {
    onDelete(investigation.id);
    setShowDeleteConfirm(false);
  };

  const tabs = [
    { id: 'overview', label: 'Resumen', icon: Eye },
    { id: 'entities', label: 'Entidades', icon: User, count: entities.length },
    { id: 'relationships', label: 'Relaciones', icon: Link },
    { id: 'history', label: 'Historial', icon: Clock, count: activity.length },
    { id: 'notes', label: 'Notas', icon: FileText }
  ];

  return (
    <div className={`bg-white rounded-lg shadow-sm border border-gray-200 ${className}`}>
      {/* Header */}
      <div className="border-b border-gray-200 p-6">
        <div className="flex items-center justify-between mb-4">
          <button
            onClick={onBack}
            className="flex items-center text-gray-600 hover:text-gray-900 transition-colors"
          >
            <ArrowLeft className="h-5 w-5 mr-2" />
            Volver a la lista
          </button>
          
          <div className="flex items-center space-x-2">
            <button
              onClick={() => onEdit(investigation)}
              className="inline-flex items-center px-3 py-2 border border-gray-300 shadow-sm text-sm leading-4 font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
            >
              <Edit className="h-4 w-4 mr-2" />
              Editar
            </button>
            
            <button
              onClick={() => setShowDeleteConfirm(true)}
              className="inline-flex items-center px-3 py-2 border border-red-300 shadow-sm text-sm leading-4 font-medium rounded-md text-red-700 bg-white hover:bg-red-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500"
            >
              <Trash2 className="h-4 w-4 mr-2" />
              Eliminar
            </button>
            
            <button className="inline-flex items-center px-3 py-2 border border-gray-300 shadow-sm text-sm leading-4 font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500">
              <Share className="h-4 w-4 mr-2" />
              Compartir
            </button>
          </div>
        </div>

        <div className="flex items-start justify-between">
          <div className="flex-1">
            <h1 className="text-2xl font-bold text-gray-900 mb-2">{investigation.title}</h1>
            <p className="text-gray-600 mb-4">{investigation.description}</p>
            
            <div className="flex items-center space-x-4">
              <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${getStatusColor(investigation.status)}`}>
                {investigation.status === 'active' ? 'Activa' : 
                 investigation.status === 'completed' ? 'Completada' : 'Archivada'}
              </span>
              
              <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${getPriorityColor(investigation.priority)}`}>
                {investigation.priority === 'critical' ? 'Crítica' :
                 investigation.priority === 'high' ? 'Alta' :
                 investigation.priority === 'medium' ? 'Media' : 'Baja'}
              </span>
              
              <span className="text-sm text-gray-500">
                <Calendar className="h-4 w-4 inline mr-1" />
                Creada: {formatDate(investigation.createdAt)}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <nav className="-mb-px flex space-x-8 px-6">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as TabType)}
                className={`py-4 px-1 border-b-2 font-medium text-sm flex items-center ${
                  activeTab === tab.id
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                <Icon className="h-4 w-4 mr-2" />
                {tab.label}
                {tab.count !== undefined && (
                  <span className="ml-2 bg-gray-100 text-gray-900 py-0.5 px-2 rounded-full text-xs">
                    {tab.count}
                  </span>
                )}
              </button>
            );
          })}
        </nav>
      </div>

      {/* Tab Content */}
      <div className="p-6">
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            <span className="ml-2 text-gray-600">Cargando...</span>
          </div>
        ) : (
          <>
            {/* Overview Tab */}
            {activeTab === 'overview' && (
              <div className="space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  <div className="bg-gray-50 rounded-lg p-4">
                    <h3 className="text-sm font-medium text-gray-900 mb-2">Entidades</h3>
                    <p className="text-2xl font-bold text-blue-600">{entities.length}</p>
                  </div>
                  <div className="bg-gray-50 rounded-lg p-4">
                    <h3 className="text-sm font-medium text-gray-900 mb-2">Relaciones</h3>
                    <p className="text-2xl font-bold text-green-600">0</p>
                  </div>
                  <div className="bg-gray-50 rounded-lg p-4">
                    <h3 className="text-sm font-medium text-gray-900 mb-2">Actividad</h3>
                    <p className="text-2xl font-bold text-purple-600">{activity.length}</p>
                  </div>
                </div>
                
                {/* Tags section removed - property doesn't exist in Investigation type */}
                
                {/* Notes section removed - property doesn't exist in Investigation type */}
              </div>
            )}

            {/* Entities Tab */}
            {activeTab === 'entities' && (
              <div>
                <div className="flex items-center justify-between mb-6">
                  <h3 className="text-lg font-medium text-gray-900">Entidades Asociadas</h3>
                  <button className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500">
                    Agregar Entidad
                  </button>
                </div>
                
                {entities.length === 0 ? (
                  <div className="text-center py-12">
                    <User className="mx-auto h-12 w-12 text-gray-400" />
                    <h3 className="mt-2 text-sm font-medium text-gray-900">No hay entidades</h3>
                    <p className="mt-1 text-sm text-gray-500">Comienza agregando entidades a esta investigación.</p>
                  </div>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {entities.map((entity) => (
                      <div key={entity.id} className="bg-white border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow">
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-2xl">{getEntityTypeIcon(entity.type)}</span>
                          <span className="text-xs text-gray-500 capitalize">{entity.type}</span>
                        </div>
                        <h4 className="font-medium text-gray-900 mb-1">{entity.name}</h4>
                        {entity.description && (
                          <p className="text-sm text-gray-600 mb-2">{entity.description}</p>
                        )}
                        <div className="flex items-center justify-between">
                          <span className="text-xs text-gray-500">
                            {entity.createdAt ? formatDate(entity.createdAt) : 'N/A'}
                          </span>
                          <button className="text-blue-600 hover:text-blue-800 text-sm">
                            Ver detalles
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Relationships Tab */}
            {activeTab === 'relationships' && (
              <div className="text-center py-12">
                <Link className="mx-auto h-12 w-12 text-gray-400" />
                <h3 className="mt-2 text-sm font-medium text-gray-900">Relaciones</h3>
                <p className="mt-1 text-sm text-gray-500">Las relaciones entre entidades se mostrarán aquí.</p>
              </div>
            )}

            {/* History Tab */}
            {activeTab === 'history' && (
              <div>
                <h3 className="text-lg font-medium text-gray-900 mb-6">Historial de Actividad</h3>
                
                <div className="flow-root">
                  <ul className="-mb-8">
                    {activity.map((item, index) => (
                      <li key={item.id}>
                        <div className="relative pb-8">
                          {index !== activity.length - 1 && (
                            <span className="absolute top-4 left-4 -ml-px h-full w-0.5 bg-gray-200" />
                          )}
                          <div className="relative flex space-x-3">
                            <div className="h-8 w-8 bg-blue-500 rounded-full flex items-center justify-center">
                              <div className="text-white">
                                {getActivityIcon(item.type)}
                              </div>
                            </div>
                            <div className="min-w-0 flex-1 pt-1.5 flex justify-between space-x-4">
                              <div>
                                <p className="text-sm text-gray-900">{item.description}</p>
                                {item.user && (
                                  <p className="text-xs text-gray-500">por {item.user}</p>
                                )}
                              </div>
                              <div className="text-right text-xs text-gray-500 whitespace-nowrap">
                                {formatDate(item.timestamp)}
                              </div>
                            </div>
                          </div>
                        </div>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            )}

            {/* Notes Tab */}
            {activeTab === 'notes' && (
              <div>
                <div className="flex items-center justify-between mb-6">
                  <h3 className="text-lg font-medium text-gray-900">Notas de la Investigación</h3>
                  <button className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500">
                    Agregar Nota
                  </button>
                </div>
                
                <div className="text-center py-12">
                  <FileText className="mx-auto h-12 w-12 text-gray-400" />
                  <h3 className="mt-2 text-sm font-medium text-gray-900">No hay notas</h3>
                  <p className="mt-1 text-sm text-gray-500">Agrega notas para documentar hallazgos importantes.</p>
                </div>
              </div>
            )}
          </>
        )}
      </div>

      {/* Delete Confirmation Modal */}
      {showDeleteConfirm && (
        <div className="fixed inset-0 z-50 overflow-y-auto">
          <div className="flex items-end justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
            <div className="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity" />
            
            <div className="inline-block align-bottom bg-white rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-lg sm:w-full">
              <div className="bg-white px-4 pt-5 pb-4 sm:p-6 sm:pb-4">
                <div className="sm:flex sm:items-start">
                  <div className="mx-auto flex-shrink-0 flex items-center justify-center h-12 w-12 rounded-full bg-red-100 sm:mx-0 sm:h-10 sm:w-10">
                    <AlertTriangle className="h-6 w-6 text-red-600" />
                  </div>
                  <div className="mt-3 text-center sm:mt-0 sm:ml-4 sm:text-left">
                    <h3 className="text-lg leading-6 font-medium text-gray-900">
                      Eliminar Investigación
                    </h3>
                    <div className="mt-2">
                      <p className="text-sm text-gray-500">
                        ¿Estás seguro de que quieres eliminar esta investigación? Esta acción no se puede deshacer.
                      </p>
                    </div>
                  </div>
                </div>
              </div>
              <div className="bg-gray-50 px-4 py-3 sm:px-6 sm:flex sm:flex-row-reverse">
                <button
                  type="button"
                  onClick={handleDelete}
                  className="w-full inline-flex justify-center rounded-md border border-transparent shadow-sm px-4 py-2 bg-red-600 text-base font-medium text-white hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 sm:ml-3 sm:w-auto sm:text-sm"
                >
                  Eliminar
                </button>
                <button
                  type="button"
                  onClick={() => setShowDeleteConfirm(false)}
                  className="mt-3 w-full inline-flex justify-center rounded-md border border-gray-300 shadow-sm px-4 py-2 bg-white text-base font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 sm:mt-0 sm:ml-3 sm:w-auto sm:text-sm"
                >
                  Cancelar
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default InvestigationDetail;
export type { ActivityItem };