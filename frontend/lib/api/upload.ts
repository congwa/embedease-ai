// 图片上传 API

import { ApiError } from "@/lib/errors";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "";

export interface ImageUploadResponse {
  id: string;
  url: string;
  thumbnail_url: string;
  filename: string;
  size: number;
  width: number;
  height: number;
  mime_type: string;
}

export interface UploadConfig {
  enabled: boolean;
  max_size_mb: number;
  max_count_per_message: number;
  allowed_types: string[];
}

/**
 * 获取上传配置
 */
export async function getUploadConfig(): Promise<UploadConfig> {
  const response = await fetch(`${API_BASE_URL}/upload/config`);
  
  if (!response.ok) {
    throw new ApiError(response.status, {
      code: `http_${response.status}`,
      message: "获取上传配置失败",
    });
  }
  
  return response.json();
}

/**
 * 上传图片
 */
export async function uploadImage(
  file: File,
  userId?: string
): Promise<ImageUploadResponse> {
  const formData = new FormData();
  formData.append("file", file);
  if (userId) {
    formData.append("user_id", userId);
  }

  const response = await fetch(`${API_BASE_URL}/upload/image`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new ApiError(response.status, {
      code: errorData.error?.code || `http_${response.status}`,
      message: errorData.error?.message || errorData.detail || "图片上传失败",
    });
  }

  return response.json();
}

/**
 * 批量上传图片
 */
export async function uploadImages(
  files: File[],
  userId?: string
): Promise<ImageUploadResponse[]> {
  const results: ImageUploadResponse[] = [];
  
  for (const file of files) {
    const result = await uploadImage(file, userId);
    results.push(result);
  }
  
  return results;
}

/**
 * 删除图片
 */
export async function deleteImage(
  imageId: string,
  userId?: string
): Promise<void> {
  const params = new URLSearchParams();
  if (userId) {
    params.append("user_id", userId);
  }

  const url = `${API_BASE_URL}/upload/image/${imageId}${params.toString() ? `?${params}` : ""}`;
  
  const response = await fetch(url, {
    method: "DELETE",
  });

  if (!response.ok) {
    throw new ApiError(response.status, {
      code: `http_${response.status}`,
      message: "删除图片失败",
    });
  }
}
