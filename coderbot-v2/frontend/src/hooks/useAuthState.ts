import { useState, useEffect } from 'react';
import { pb, UserRecord, getCurrentUser } from '@/integrations/pocketbase/client';

/**
 * Hook reativo que monitora mudanças no estado de autenticação do PocketBase.
 * 
 * **Problema resolvido:**
 * `getCurrentUser()` retorna um snapshot não-reativo. Se o usuário faz logout,
 * os componentes não re-renderizam automaticamente.
 * 
 * **Solução:**
 * Este hook se subscreve ao `pb.authStore.onChange()` para forçar re-render
 * sempre que o estado de autenticação mudar (login, logout, token expirado).
 * 
 * @returns currentUser - Usuário autenticado ou undefined
 * @returns isAuthenticated - Boolean indicando se há sessão válida
 * @returns isLoading - Boolean durante carregamento inicial
 */
export const useAuthState = () => {
  const [currentUser, setCurrentUser] = useState<UserRecord | undefined>(() => getCurrentUser());
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(() => pb.authStore.isValid);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // Sincronizar estado inicial
    setCurrentUser(getCurrentUser());
    setIsAuthenticated(pb.authStore.isValid);
    setIsLoading(false);

    // Subscrever a mudanças no authStore
    const unsubscribe = pb.authStore.onChange((token, model) => {
      console.log('🔄 [useAuthState] Auth changed:', {
        hasToken: !!token,
        hasModel: !!model,
        userId: model?.id || 'none'
      });

      setCurrentUser(model ? (model as unknown as UserRecord) : undefined);
      setIsAuthenticated(!!token && !!model);
    });

    // Cleanup: desinscrever quando componente desmontar
    return () => {
      unsubscribe();
    };
  }, []);

  return {
    currentUser,
    isAuthenticated,
    isLoading
  };
};
