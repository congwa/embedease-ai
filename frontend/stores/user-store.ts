/**
 * 用户状态管理 Store
 */

import { create } from "zustand";
import { persist } from "zustand/middleware";
import { createUser, getUser } from "@/lib/api";

const USER_ID_KEY = "embed_ai_user_id";

interface UserState {
  userId: string | null;
  isLoading: boolean;
  isInitialized: boolean;

  initUser: () => Promise<void>;
  clearUser: () => void;
  setUserId: (id: string) => void;
}

export const useUserStore = create<UserState>()(
  persist(
    (set, get) => ({
      userId: null,
      isLoading: true,
      isInitialized: false,

      initUser: async () => {
        if (get().isInitialized) return;

        set({ isLoading: true });
        try {
          const storedUserId = localStorage.getItem(USER_ID_KEY);

          if (storedUserId) {
            const user = await getUser(storedUserId);
            if (user.exists) {
              set({ userId: storedUserId, isLoading: false, isInitialized: true });
              console.log("[UserStore] 已恢复用户:", storedUserId);
              return;
            }
          }

          const response = await createUser();
          localStorage.setItem(USER_ID_KEY, response.user_id);
          set({ userId: response.user_id, isLoading: false, isInitialized: true });
          console.log("[UserStore] 已创建新用户:", response.user_id);
        } catch (error) {
          console.error("[UserStore] 初始化失败:", error);
          const tempId = crypto.randomUUID();
          localStorage.setItem(USER_ID_KEY, tempId);
          set({ userId: tempId, isLoading: false, isInitialized: true });
        }
      },

      clearUser: () => {
        localStorage.removeItem(USER_ID_KEY);
        set({ userId: null, isInitialized: false });
      },

      setUserId: (id: string) => {
        localStorage.setItem(USER_ID_KEY, id);
        set({ userId: id });
      },
    }),
    {
      name: "user-storage",
      partialize: (state) => ({ userId: state.userId }),
    }
  )
);
