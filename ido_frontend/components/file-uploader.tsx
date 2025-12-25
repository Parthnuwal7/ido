'use client';

import { useState, useCallback, useRef } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Upload, FileArchive, Check } from 'lucide-react';
import { cn } from '@/lib/utils';

interface FileUploaderProps {
    onFileSelect: (file: File) => void;
    disabled?: boolean;
    accept?: string;
}

export function FileUploader({ onFileSelect, disabled, accept = '.zip' }: FileUploaderProps) {
    const [isDragging, setIsDragging] = useState(false);
    const [selectedFile, setSelectedFile] = useState<File | null>(null);
    const fileInputRef = useRef<HTMLInputElement>(null);

    const handleDrag = useCallback((e: React.DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
    }, []);

    const handleDragIn = useCallback((e: React.DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
        if (e.dataTransfer.items && e.dataTransfer.items.length > 0) {
            setIsDragging(true);
        }
    }, []);

    const handleDragOut = useCallback((e: React.DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
        setIsDragging(false);
    }, []);

    const handleDrop = useCallback((e: React.DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
        setIsDragging(false);

        if (disabled) return;

        const files = e.dataTransfer.files;
        if (files && files.length > 0) {
            const file = files[0];
            if (file.name.endsWith('.zip')) {
                setSelectedFile(file);
                onFileSelect(file);
            }
        }
    }, [disabled, onFileSelect]);

    const handleFileInput = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
        const files = e.target.files;
        if (files && files.length > 0) {
            setSelectedFile(files[0]);
            onFileSelect(files[0]);
        }
    }, [onFileSelect]);

    const handleClick = useCallback(() => {
        if (!disabled) {
            fileInputRef.current?.click();
        }
    }, [disabled]);

    const formatFileSize = (bytes: number) => {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    };

    return (
        <div className="w-full">
            <Card
                onClick={handleClick}
                onDragEnter={handleDragIn}
                onDragLeave={handleDragOut}
                onDragOver={handleDrag}
                onDrop={handleDrop}
                className={cn(
                    'border-2 border-dashed cursor-pointer transition-all duration-200',
                    isDragging && 'border-primary bg-primary/5 scale-[1.02]',
                    disabled && 'opacity-50 cursor-not-allowed',
                    !isDragging && !disabled && 'hover:border-primary/50 hover:bg-accent/50'
                )}
            >
                <CardContent className="flex flex-col items-center justify-center py-10 px-6">
                    <input
                        ref={fileInputRef}
                        type="file"
                        accept={accept}
                        onChange={handleFileInput}
                        className="hidden"
                        disabled={disabled}
                    />

                    {selectedFile ? (
                        <div className="text-center animate-in fade-in-50 zoom-in-95">
                            <div className="w-16 h-16 mx-auto mb-4 bg-primary/10 rounded-full flex items-center justify-center">
                                <Check className="w-8 h-8 text-primary" />
                            </div>
                            <p className="text-lg font-medium">{selectedFile.name}</p>
                            <p className="text-sm text-muted-foreground">{formatFileSize(selectedFile.size)}</p>
                        </div>
                    ) : (
                        <>
                            <div className="w-16 h-16 mx-auto mb-4 bg-muted rounded-full flex items-center justify-center">
                                {isDragging ? (
                                    <FileArchive className="w-8 h-8 text-primary" />
                                ) : (
                                    <Upload className="w-8 h-8 text-muted-foreground" />
                                )}
                            </div>
                            <p className="text-lg font-medium">
                                {isDragging ? 'Drop your file here' : 'Drag & drop your ZIP file'}
                            </p>
                            <p className="text-sm text-muted-foreground">or click to browse</p>
                            <p className="text-xs text-muted-foreground mt-2">
                                Supports YouTube Takeout ZIP files
                            </p>
                        </>
                    )}
                </CardContent>
            </Card>
        </div>
    );
}
