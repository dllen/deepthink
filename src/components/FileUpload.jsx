import React, { useState } from 'react';

const FileUpload = ({ onFileUpload }) => {
  const [fileName, setFileName] = useState('');

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      if (file.name.endsWith('.sqlite')) {
        setFileName(file.name);
        onFileUpload(file);
      } else {
        alert('请上传有效的SQLite文件(.sqlite)');
        e.target.value = null; // 重置输入
      }
    }
  };

  return (
    <div className="mb-6">
      <label className="block text-sm font-medium text-gray-700 mb-2">
        上传SQLite数据库文件
      </label>
      <div className="flex items-center space-x-2">
        <label className="flex flex-col items-center justify-center w-full h-32 border-2 border-dashed border-gray-300 rounded-lg cursor-pointer bg-gray-50 hover:bg-gray-100 transition-colors">
          <div className="flex flex-col items-center justify-center pt-5 pb-6">
            <svg className="w-8 h-8 mb-4 text-gray-500" aria-hidden="true" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 20 16">
              <path stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 13h3a3 3 0 0 0 0-6h-.025A5.56 5.56 0 0 0 16 6.5 5.6 5.6 0 0 0 5.207 5.021C5.137 5.017 5.071 5 5 5a4 4 0 0 0 0 8h2.167M10 15V6m0 0L8 8m2-2 2 2"/>
            </svg>
            <p className="mb-2 text-sm text-gray-500">
              <span className="font-semibold">点击上传</span> 或拖拽文件到此处
            </p>
            <p className="text-xs text-gray-500">SQLite文件 (.sqlite)</p>
          </div>
          <input 
            type="file" 
            className="hidden" 
            accept=".sqlite" 
            onChange={handleFileChange} 
          />
        </label>
      </div>
      {fileName && (
        <p className="mt-2 text-sm text-gray-600">
          已选择: <span className="font-medium">{fileName}</span>
        </p>
      )}
    </div>
  );
};

export default FileUpload;