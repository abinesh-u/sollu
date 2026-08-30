import * as LucideIcons from 'lucide-react';
import type { ClassInfo } from './types';

// Fallback lookup if API hasn't loaded yet
export const getFallbackLabel = (taskClass: string) => {
  const map: Record<string, string> = {
    research: 'Grounded Research',
    watch_price: 'Watch Condition',
  };
  return map[taskClass] || taskClass;
};

// Returns a React node for the icon name
export const getIconByName = (iconName: string | undefined, size = 16) => {
  if (!iconName) iconName = 'FileText';
  const IconComponent = (LucideIcons as any)[iconName] || LucideIcons.FileText;
  return <IconComponent size={size} strokeWidth={1.5} />;
};

export const getClassIcon = (taskClass: string, classesData: ClassInfo[], size = 16) => {
  const cls = classesData.find(c => c.class === taskClass);
  return getIconByName(cls?.ui_icon_name, size);
};
