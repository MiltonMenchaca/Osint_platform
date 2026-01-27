import React, { useState, useEffect } from 'react';
import type { Investigation } from '../types';
import { 
  X,
  FileText,
  Tag,
  AlertTriangle,
  Check
} from 'lucide-react';

interface InvestigationFormData {
  title: string;
  description: string;
  status: Investigation['status'];
  priority: Investigation['priority'];
  tags?: string[];
}

interface InvestigationFormProps {
  investigation?: Investigation | null;
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (data: InvestigationFormData) => Promise<void>;
  loading?: boolean;
  className?: string;
}

const InvestigationForm: React.FC<InvestigationFormProps> = ({
  investigation,
  isOpen,
  onClose,
  onSubmit,
  loading = false,
  className = ''
}) => {
  const [formData, setFormData] = useState<InvestigationFormData>({
    title: '',
    description: '',
    status: 'active',
    priority: 'medium',
    tags: []
  });
  
  const [errors, setErrors] = useState<Partial<InvestigationFormData>>({});
  const [tagInput, setTagInput] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Initialize form data when investigation changes
  useEffect(() => {
    if (investigation) {
      setFormData({
        title: investigation.title || '',
        description: investigation.description || '',
        status: investigation.status,
        priority: investigation.priority,
        tags: [], // investigation.tags || [], // tags property doesn't exist in Investigation type
        // notes: investigation.notes || '' // Property doesn't exist in Investigation type
      });
    } else {
      setFormData({
        title: '',
        description: '',
        status: 'active',
        priority: 'medium',
        tags: []
      });
    }
    setErrors({});
  }, [investigation, isOpen]);

  const statusOptions: { value: Investigation['status']; label: string; description: string }[] = [
    { value: 'active', label: 'Activa', description: 'Investigación en curso' },
    { value: 'completed', label: 'Completada', description: 'Investigación finalizada' },
    { value: 'archived', label: 'Archivada', description: 'Investigación archivada' }
  ];

  const priorityOptions: { value: Investigation['priority']; label: string; color: string; description: string }[] = [
    { value: 'critical', label: 'Crítica', color: 'text-red-600 bg-red-50 border-red-200', description: 'Requiere atención inmediata' },
    { value: 'high', label: 'Alta', color: 'text-orange-600 bg-orange-50 border-orange-200', description: 'Alta prioridad' },
    { value: 'medium', label: 'Media', color: 'text-yellow-600 bg-yellow-50 border-yellow-200', description: 'Prioridad normal' },
    { value: 'low', label: 'Baja', color: 'text-green-600 bg-green-50 border-green-200', description: 'Baja prioridad' }
  ];

  const validateForm = (): boolean => {
    const newErrors: Partial<InvestigationFormData> = {};

    if (!formData.title.trim()) {
      newErrors.title = 'El título es obligatorio';
    } else if (formData.title.length < 3) {
      newErrors.title = 'El título debe tener al menos 3 caracteres';
    } else if (formData.title.length > 200) {
      newErrors.title = 'El título no puede exceder 200 caracteres';
    }

    if (!formData.description.trim()) {
      newErrors.description = 'La descripción es obligatoria';
    } else if (formData.description.length < 10) {
      newErrors.description = 'La descripción debe tener al menos 10 caracteres';
    } else if (formData.description.length > 1000) {
      newErrors.description = 'La descripción no puede exceder 1000 caracteres';
    }

    // Notes validation removed as property doesn't exist in Investigation type

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!validateForm()) {
      return;
    }

    setIsSubmitting(true);
    try {
      await onSubmit(formData);
      onClose();
    } catch (error) {
      console.error('Error submitting form:', error);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleInputChange = (field: keyof InvestigationFormData, value: any) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    // Clear error when user starts typing
    if (errors[field]) {
      setErrors(prev => ({ ...prev, [field]: undefined }));
    }
  };

  const handleAddTag = () => {
    const tag = tagInput.trim();
    if (tag && !formData.tags?.includes(tag)) {
      handleInputChange('tags', [...(formData.tags || []), tag]);
      setTagInput('');
    }
  };

  const handleRemoveTag = (tagToRemove: string) => {
    handleInputChange('tags', formData.tags?.filter(tag => tag !== tagToRemove) || []);
  };

  const handleTagInputKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleAddTag();
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex items-center justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
        {/* Background overlay */}
        <div 
          className="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity"
          onClick={onClose}
        />

        {/* Modal */}
        <div className={`inline-block align-bottom bg-white rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-2xl sm:w-full ${className}`}>
          <form onSubmit={handleSubmit}>
            {/* Header */}
            <div className="bg-white px-6 py-4 border-b border-gray-200">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-medium text-gray-900">
                  {investigation ? 'Editar Investigación' : 'Nueva Investigación'}
                </h3>
                <button
                  type="button"
                  onClick={onClose}
                  className="text-gray-400 hover:text-gray-600 focus:outline-none focus:text-gray-600"
                >
                  <X className="h-6 w-6" />
                </button>
              </div>
            </div>

            {/* Form Content */}
            <div className="bg-white px-6 py-4 space-y-6 max-h-96 overflow-y-auto">
              {/* Title */}
              <div>
                <label htmlFor="title" className="block text-sm font-medium text-gray-700 mb-2">
                  <FileText className="h-4 w-4 inline mr-1" />
                  Título *
                </label>
                <input
                  type="text"
                  id="title"
                  value={formData.title}
                  onChange={(e) => handleInputChange('title', e.target.value)}
                  className={`w-full px-3 py-2 border rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                    errors.title ? 'border-red-300 focus:border-red-500' : 'border-gray-300 focus:border-blue-500'
                  }`}
                  placeholder="Ingresa el título de la investigación..."
                  maxLength={200}
                />
                {errors.title && (
                  <p className="mt-1 text-sm text-red-600">{errors.title}</p>
                )}
                <p className="mt-1 text-xs text-gray-500">
                  {formData.title.length}/200 caracteres
                </p>
              </div>

              {/* Description */}
              <div>
                <label htmlFor="description" className="block text-sm font-medium text-gray-700 mb-2">
                  Descripción *
                </label>
                <textarea
                  id="description"
                  value={formData.description}
                  onChange={(e) => handleInputChange('description', e.target.value)}
                  rows={4}
                  className={`w-full px-3 py-2 border rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none ${
                    errors.description ? 'border-red-300 focus:border-red-500' : 'border-gray-300 focus:border-blue-500'
                  }`}
                  placeholder="Describe el objetivo y alcance de la investigación..."
                  maxLength={1000}
                />
                {errors.description && (
                  <p className="mt-1 text-sm text-red-600">{errors.description}</p>
                )}
                <p className="mt-1 text-xs text-gray-500">
                  {formData.description.length}/1000 caracteres
                </p>
              </div>

              {/* Status and Priority */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Status */}
                <div>
                  <label htmlFor="status" className="block text-sm font-medium text-gray-700 mb-2">
                    <Tag className="h-4 w-4 inline mr-1" />
                    Estado
                  </label>
                  <select
                    id="status"
                    value={formData.status}
                    onChange={(e) => handleInputChange('status', e.target.value as Investigation['status'])}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  >
                    {statusOptions.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label} - {option.description}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Priority */}
                <div>
                  <label htmlFor="priority" className="block text-sm font-medium text-gray-700 mb-2">
                    <AlertTriangle className="h-4 w-4 inline mr-1" />
                    Prioridad
                  </label>
                  <select
                    id="priority"
                    value={formData.priority}
                    onChange={(e) => handleInputChange('priority', e.target.value as Investigation['priority'])}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  >
                    {priorityOptions.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label} - {option.description}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Tags */}
              <div>
                <label htmlFor="tags" className="block text-sm font-medium text-gray-700 mb-2">
                  Etiquetas
                </label>
                <div className="flex flex-wrap gap-2 mb-2">
                  {formData.tags?.map((tag) => (
                    <span
                      key={tag}
                      className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800"
                    >
                      {tag}
                      <button
                        type="button"
                        onClick={() => handleRemoveTag(tag)}
                        className="ml-1 h-3 w-3 text-blue-600 hover:text-blue-800"
                      >
                        <X className="h-3 w-3" />
                      </button>
                    </span>
                  ))}
                </div>
                <div className="flex">
                  <input
                    type="text"
                    value={tagInput}
                    onChange={(e) => setTagInput(e.target.value)}
                    onKeyPress={handleTagInputKeyPress}
                    className="flex-1 px-3 py-2 border border-gray-300 rounded-l-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    placeholder="Agregar etiqueta..."
                  />
                  <button
                    type="button"
                    onClick={handleAddTag}
                    className="px-4 py-2 bg-blue-600 text-white rounded-r-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
                  >
                    Agregar
                  </button>
                </div>
              </div>


            </div>

            {/* Footer */}
            <div className="bg-gray-50 px-6 py-4 flex justify-end space-x-3">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                disabled={isSubmitting}
              >
                Cancelar
              </button>
              <button
                type="submit"
                disabled={isSubmitting || loading}
                className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isSubmitting || loading ? (
                  <>
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                    {investigation ? 'Actualizando...' : 'Creando...'}
                  </>
                ) : (
                  <>
                    <Check className="h-4 w-4 mr-2" />
                    {investigation ? 'Actualizar' : 'Crear'} Investigación
                  </>
                )}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};

export default InvestigationForm;
export type { InvestigationFormData };