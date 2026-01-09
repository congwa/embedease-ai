"use client";

import { useState } from "react";
import { X, ChevronLeft, ChevronRight, Download, ZoomIn } from "lucide-react";
import { cn } from "@/lib/utils";

export interface ImageInfo {
  id: string;
  url: string;
  thumbnail_url?: string;
  filename?: string;
  width?: number;
  height?: number;
}

interface ImageGalleryProps {
  images: ImageInfo[];
  className?: string;
}

export function ImageGallery({ images, className }: ImageGalleryProps) {
  const [lightboxOpen, setLightboxOpen] = useState(false);
  const [currentIndex, setCurrentIndex] = useState(0);

  if (!images || images.length === 0) return null;

  const openLightbox = (index: number) => {
    setCurrentIndex(index);
    setLightboxOpen(true);
  };

  const closeLightbox = () => {
    setLightboxOpen(false);
  };

  const goToPrev = () => {
    setCurrentIndex((prev) => (prev > 0 ? prev - 1 : images.length - 1));
  };

  const goToNext = () => {
    setCurrentIndex((prev) => (prev < images.length - 1 ? prev + 1 : 0));
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Escape") closeLightbox();
    if (e.key === "ArrowLeft") goToPrev();
    if (e.key === "ArrowRight") goToNext();
  };

  const downloadImage = (image: ImageInfo) => {
    const link = document.createElement("a");
    link.href = image.url;
    link.download = image.filename || `image-${image.id}`;
    link.click();
  };

  return (
    <>
      {/* 图片网格 */}
      <div
        className={cn(
          "grid gap-2",
          images.length === 1 && "grid-cols-1",
          images.length === 2 && "grid-cols-2",
          images.length >= 3 && "grid-cols-3",
          className
        )}
      >
        {images.map((image, index) => (
          <div
            key={image.id}
            className="relative group cursor-pointer overflow-hidden rounded-lg"
            onClick={() => openLightbox(index)}
          >
            <img
              src={image.thumbnail_url || image.url}
              alt={image.filename || `图片 ${index + 1}`}
              className={cn(
                "w-full object-cover transition-transform group-hover:scale-105",
                images.length === 1 ? "max-h-64" : "h-24"
              )}
              loading="lazy"
            />
            <div className="absolute inset-0 bg-black/0 group-hover:bg-black/20 transition-colors flex items-center justify-center">
              <ZoomIn className="w-6 h-6 text-white opacity-0 group-hover:opacity-100 transition-opacity" />
            </div>
          </div>
        ))}
      </div>

      {/* Lightbox */}
      {lightboxOpen && (
        <div
          className="fixed inset-0 z-50 bg-black/90 flex items-center justify-center"
          onClick={closeLightbox}
          onKeyDown={handleKeyDown}
          tabIndex={0}
        >
          {/* 关闭按钮 */}
          <button
            className="absolute top-4 right-4 p-2 text-white hover:bg-white/10 rounded-full transition-colors"
            onClick={closeLightbox}
          >
            <X className="w-6 h-6" />
          </button>

          {/* 下载按钮 */}
          <button
            className="absolute top-4 right-16 p-2 text-white hover:bg-white/10 rounded-full transition-colors"
            onClick={(e) => {
              e.stopPropagation();
              downloadImage(images[currentIndex]);
            }}
          >
            <Download className="w-6 h-6" />
          </button>

          {/* 图片计数 */}
          {images.length > 1 && (
            <div className="absolute top-4 left-4 text-white text-sm">
              {currentIndex + 1} / {images.length}
            </div>
          )}

          {/* 上一张 */}
          {images.length > 1 && (
            <button
              className="absolute left-4 p-2 text-white hover:bg-white/10 rounded-full transition-colors"
              onClick={(e) => {
                e.stopPropagation();
                goToPrev();
              }}
            >
              <ChevronLeft className="w-8 h-8" />
            </button>
          )}

          {/* 图片 */}
          <img
            src={images[currentIndex].url}
            alt={images[currentIndex].filename || `图片 ${currentIndex + 1}`}
            className="max-w-[90vw] max-h-[90vh] object-contain"
            onClick={(e) => e.stopPropagation()}
          />

          {/* 下一张 */}
          {images.length > 1 && (
            <button
              className="absolute right-4 p-2 text-white hover:bg-white/10 rounded-full transition-colors"
              onClick={(e) => {
                e.stopPropagation();
                goToNext();
              }}
            >
              <ChevronRight className="w-8 h-8" />
            </button>
          )}
        </div>
      )}
    </>
  );
}

export default ImageGallery;
