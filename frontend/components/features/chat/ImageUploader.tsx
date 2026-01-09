"use client";

import { useState, useRef, useCallback } from "react";
import { ImagePlus, X, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { uploadImage, type ImageUploadResponse } from "@/lib/api/upload";

export interface UploadedImage extends ImageUploadResponse {
  isUploading?: boolean;
  error?: string;
}

interface ImageUploaderProps {
  images: UploadedImage[];
  onImagesChange: (images: UploadedImage[]) => void;
  maxCount?: number;
  maxSizeMB?: number;
  allowedTypes?: string[];
  userId?: string;
  disabled?: boolean;
  className?: string;
}

export function ImageUploader({
  images,
  onImagesChange,
  maxCount = 5,
  maxSizeMB = 10,
  allowedTypes = ["image/jpeg", "image/png", "image/webp", "image/gif"],
  userId,
  disabled = false,
  className,
}: ImageUploaderProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging] = useState(false);

  const handleFileSelect = useCallback(
    async (files: FileList | null) => {
      if (!files || files.length === 0) return;

      const remainingSlots = maxCount - images.length;
      if (remainingSlots <= 0) return;

      const filesToUpload = Array.from(files).slice(0, remainingSlots);

      for (const file of filesToUpload) {
        // 验证文件类型
        if (!allowedTypes.includes(file.type)) {
          console.warn(`不支持的文件类型: ${file.type}`);
          continue;
        }

        // 验证文件大小
        if (file.size > maxSizeMB * 1024 * 1024) {
          console.warn(`文件太大: ${file.name}`);
          continue;
        }

        // 添加临时占位
        const tempId = `temp-${Date.now()}-${Math.random()}`;
        const tempImage: UploadedImage = {
          id: tempId,
          url: URL.createObjectURL(file),
          thumbnail_url: URL.createObjectURL(file),
          filename: file.name,
          size: file.size,
          width: 0,
          height: 0,
          mime_type: file.type,
          isUploading: true,
        };

        const newImages = [...images, tempImage];
        onImagesChange(newImages);

        try {
          const result = await uploadImage(file, userId);
          const updatedImages = newImages.map((img: UploadedImage) =>
            img.id === tempId
              ? { ...result, isUploading: false }
              : img
          );
          onImagesChange(updatedImages);
        } catch (error) {
          const errorImages = newImages.map((img: UploadedImage) =>
            img.id === tempId
              ? { ...img, isUploading: false, error: String(error) }
              : img
          );
          onImagesChange(errorImages);
        }
      }
    },
    [images, maxCount, maxSizeMB, allowedTypes, userId, onImagesChange]
  );

  const handleRemoveImage = useCallback(
    (imageId: string) => {
      onImagesChange(images.filter((img) => img.id !== imageId));
    },
    [images, onImagesChange]
  );

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);
      handleFileSelect(e.dataTransfer.files);
    },
    [handleFileSelect]
  );

  const canAddMore = images.length < maxCount && !disabled;

  return (
    <div className={cn("flex flex-col gap-2", className)}>
      {/* 已上传图片预览 */}
      {images.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {images.map((image) => (
            <div
              key={image.id}
              className="relative group w-16 h-16 rounded-lg overflow-hidden border border-zinc-200 dark:border-zinc-700"
            >
              <img
                src={image.thumbnail_url || image.url}
                alt={image.filename}
                className="w-full h-full object-cover"
              />
              {image.isUploading && (
                <div className="absolute inset-0 bg-black/50 flex items-center justify-center">
                  <Loader2 className="w-4 h-4 text-white animate-spin" />
                </div>
              )}
              {image.error && (
                <div className="absolute inset-0 bg-red-500/50 flex items-center justify-center">
                  <X className="w-4 h-4 text-white" />
                </div>
              )}
              {!image.isUploading && !disabled && (
                <button
                  type="button"
                  onClick={() => handleRemoveImage(image.id)}
                  className="absolute top-0.5 right-0.5 w-5 h-5 rounded-full bg-black/60 text-white opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center"
                >
                  <X className="w-3 h-3" />
                </button>
              )}
            </div>
          ))}
        </div>
      )}

      {/* 上传按钮 */}
      {canAddMore && (
        <div
          className={cn(
            "flex items-center justify-center w-8 h-8 rounded-lg cursor-pointer transition-colors",
            isDragging
              ? "bg-blue-100 dark:bg-blue-900/30 border-2 border-dashed border-blue-400"
              : "hover:bg-zinc-100 dark:hover:bg-zinc-800"
          )}
          onClick={() => fileInputRef.current?.click()}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
        >
          <ImagePlus className="w-5 h-5 text-zinc-500" />
        </div>
      )}

      <input
        ref={fileInputRef}
        type="file"
        accept={allowedTypes.join(",")}
        multiple
        onChange={(e) => handleFileSelect(e.target.files)}
        className="hidden"
      />
    </div>
  );
}

export default ImageUploader;
