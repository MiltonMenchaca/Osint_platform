import React from 'react';
import { User, Building, Globe, Server, Mail, Phone, MapPin, Activity } from 'lucide-react';

interface EntityTypeSelectorProps {
  value: string;
  onChange: (type: string) => void;
  disabled?: boolean;
  error?: string;
  className?: string;
}

const EntityTypeSelector: React.FC<EntityTypeSelectorProps> = ({
  value,
  onChange,
  disabled = false,
  className
}) => {
  const entityTypes = [
    { value: 'person', label: 'Persona', icon: User, description: 'Individuo o persona física' },
    { value: 'organization', label: 'Organización', icon: Building, description: 'Empresa, institución o grupo' },
    { value: 'domain', label: 'Dominio', icon: Globe, description: 'Dominio web o URL' },
    { value: 'ip', label: 'Dirección IP', icon: Server, description: 'Dirección IP o servidor' },
    { value: 'port', label: 'Puerto', icon: Activity, description: 'Puerto de red expuesto' },
    { value: 'service', label: 'Servicio', icon: Activity, description: 'Servicio detectado en red' },
    { value: 'email', label: 'Email', icon: Mail, description: 'Dirección de correo electrónico' },
    { value: 'phone', label: 'Teléfono', icon: Phone, description: 'Número de teléfono' },
    { value: 'location', label: 'Ubicación', icon: MapPin, description: 'Ubicación geográfica' }
  ];



  return (
    <div className={className}>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
        disabled={disabled}
      >
        <option value="">Selecciona un tipo de entidad</option>
        {entityTypes.map((type) => (
          <option key={type.value} value={type.value}>
            {type.label}
          </option>
        ))}
      </select>

    </div>
  );
};

// Componente alternativo con cards para mejor UX
export const EntityTypeGrid: React.FC<EntityTypeSelectorProps & { onTypeSelect?: (type: string) => void }> = ({
  value,
  onChange,
  onTypeSelect,
  disabled = false
}) => {
  const entityTypes = [
    { value: 'person', label: 'Persona', icon: User, description: 'Individuo o persona física', color: 'blue' },
    { value: 'organization', label: 'Organización', icon: Building, description: 'Empresa, institución o grupo', color: 'green' },
    { value: 'domain', label: 'Dominio', icon: Globe, description: 'Dominio web o URL', color: 'purple' },
    { value: 'ip', label: 'Dirección IP', icon: Server, description: 'Dirección IP o servidor', color: 'red' },
    { value: 'port', label: 'Puerto', icon: Activity, description: 'Puerto de red expuesto', color: 'teal' },
    { value: 'service', label: 'Servicio', icon: Activity, description: 'Servicio detectado en red', color: 'orange' },
    { value: 'email', label: 'Email', icon: Mail, description: 'Dirección de correo electrónico', color: 'yellow' },
    { value: 'phone', label: 'Teléfono', icon: Phone, description: 'Número de teléfono', color: 'indigo' },
    { value: 'location', label: 'Ubicación', icon: MapPin, description: 'Ubicación geográfica', color: 'pink' }
  ];

  const getButtonClasses = (isSelected: boolean) => {
    return isSelected 
      ? 'bg-blue-600 text-white border-blue-600' 
      : 'bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-300 border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-600';
  };

  const getIconColor = (isSelected: boolean) => {
    return isSelected ? 'text-white' : 'text-gray-500 dark:text-gray-400';
  };

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
      {entityTypes.map((type) => {
        const isSelected = value === type.value;
        const IconComponent = type.icon;
        
        return (
          <button
            key={type.value}
            type="button"
            onClick={() => {
              onChange(type.value);
              onTypeSelect?.(type.value);
            }}
            disabled={disabled}
            className={`w-full text-left p-3 border rounded-lg transition-colors min-h-[80px] ${getButtonClasses(isSelected)}`}
          >
            <div className="flex items-center mb-2">
              <IconComponent className={`mr-2 ${getIconColor(isSelected)}`} size={20} />
              <span className="font-medium">{type.label}</span>
            </div>
            <p className={`text-sm mb-0 ${isSelected ? 'text-white/70' : 'text-gray-500 dark:text-gray-400'}`}>
              {type.description}
            </p>
          </button>
        );
      })}
    </div>
  );
};

export default EntityTypeSelector;
