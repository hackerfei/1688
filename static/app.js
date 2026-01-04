// 1688 Quote System - Frontend JavaScript

document.addEventListener('DOMContentLoaded', function() {
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('file-input');
    const previewContainer = document.getElementById('preview-container');
    const previewImage = document.getElementById('preview-image');
    const removeBtn = document.getElementById('remove-btn');
    const searchBtn = document.getElementById('search-btn');
    const resultsSection = document.getElementById('results-section');
    const resultsCount = document.getElementById('results-count');
    const productsBody = document.getElementById('products-body');
    const viewMoreLink = document.getElementById('view-more-link');
    
    // 弹窗元素
    const modalOverlay = document.getElementById('modal-overlay');
    const modalClose = document.getElementById('modal-close');

    let selectedFile = null;
    window.allProducts = []; // 存储所有产品数据（暴露到全局）
    const USD_RATE = 7.2;
    
    // 关闭弹窗
    modalClose.addEventListener('click', closeModal);
    modalOverlay.addEventListener('click', (e) => {
        if (e.target === modalOverlay) closeModal();
    });
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') closeModal();
    });
    
    function closeModal() {
        modalOverlay.classList.remove('show');
        document.body.style.overflow = '';
    }
    
    function openModal(product) {
        const quote = calculateQuote(product);
        
        // 填充弹窗内容
        document.getElementById('modal-image').src = product.image_url || '/static/placeholder.png';
        document.getElementById('modal-title').textContent = product.title || 'Unknown Product';
        document.getElementById('modal-price-cny').textContent = `¥${product.price || '-'}`;
        document.getElementById('modal-price-usd').textContent = `$${quote.costUSD}`;
        document.getElementById('modal-suggested-price').textContent = `$${quote.suggestedPrice}`;
        document.getElementById('modal-margin').textContent = `${quote.profitMargin}%`;
        document.getElementById('modal-1688-link').href = product.product_url || '#';
        
        // 构建徽章
        let badgesHtml = '';
        if (product.super_factory) {
            badgesHtml += '<span class="modal-badge super">⭐ Super Factory</span>';
        }
        if (product.is_choice) {
            badgesHtml += '<span class="modal-badge choice">Choice</span>';
        }
        if (product.verified_supplier) {
            badgesHtml += '<span class="modal-badge verified">✓ Verified</span>';
        }
        if (product.repurchase_rate) {
            const rateNum = parseInt(product.repurchase_rate);
            badgesHtml += `<span class="modal-badge ${rateNum >= 50 ? 'rate-high' : ''}">回购率 ${product.repurchase_rate}</span>`;
        }
        if (product.sold) {
            badgesHtml += `<span class="modal-badge sales">📦 ${product.sold}</span>`;
        }
        document.getElementById('modal-badges').innerHTML = badgesHtml;
        
        // 构建规格信息
        let specsHtml = '';
        specsHtml += `<div class="spec-row"><span class="spec-name">Weight</span><span class="spec-value">${product.weight ? product.weight + 'g' : '-'}</span></div>`;
        specsHtml += `<div class="spec-row"><span class="spec-name">Shipping</span><span class="spec-value">${product.shipping || '-'}</span></div>`;
        specsHtml += `<div class="spec-row"><span class="spec-name">MOQ</span><span class="spec-value">${product.min_order || '-'}</span></div>`;
        if (product.origin) {
            specsHtml += `<div class="spec-row"><span class="spec-name">Origin</span><span class="spec-value">${product.origin}</span></div>`;
        }
        if (product.material) {
            specsHtml += `<div class="spec-row"><span class="spec-name">Material</span><span class="spec-value">${product.material}</span></div>`;
        }
        if (product.size) {
            specsHtml += `<div class="spec-row"><span class="spec-name">Size</span><span class="spec-value">${product.size}</span></div>`;
        }
        document.getElementById('modal-specs').innerHTML = specsHtml;
        
        // 供应商信息
        let supplierHtml = `
            <div class="supplier-row">
                <span class="supplier-label">Supplier</span>
                <span class="supplier-value">${product.supplier || 'Unknown'}</span>
            </div>
        `;
        if (product.years_on_platform) {
            supplierHtml += `
                <div class="supplier-row">
                    <span class="supplier-label">Years on Platform</span>
                    <span class="supplier-value">${product.years_on_platform} years</span>
                </div>
            `;
        }
        document.getElementById('modal-supplier').innerHTML = supplierHtml;
        
        // 显示弹窗
        modalOverlay.classList.add('show');
        document.body.style.overflow = 'hidden';
    }
    
    // 暴露给全局使用
    window.openProductModal = function(index) {
        if (window.allProducts[index]) {
            openModal(window.allProducts[index]);
        }
    };

    // 拖拽上传
    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('drag-over');
    });

    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('drag-over');
    });

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('drag-over');
        const files = e.dataTransfer.files;
        if (files.length > 0 && files[0].type.startsWith('image/')) {
            handleFile(files[0]);
        }
    });

    // 点击上传
    dropZone.addEventListener('click', () => {
        fileInput.click();
    });

    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handleFile(e.target.files[0]);
        }
    });

    // 处理文件
    function handleFile(file) {
        selectedFile = file;
        const reader = new FileReader();
        reader.onload = (e) => {
            previewImage.src = e.target.result;
            dropZone.classList.add('hidden');
            previewContainer.classList.remove('hidden');
            searchBtn.disabled = false;
        };
        reader.readAsDataURL(file);
    }

    // 移除预览
    removeBtn.addEventListener('click', () => {
        selectedFile = null;
        previewImage.src = '';
        dropZone.classList.remove('hidden');
        previewContainer.classList.add('hidden');
        searchBtn.disabled = true;
        fileInput.value = '';
    });

    // 搜索按钮
    searchBtn.addEventListener('click', async () => {
        if (!selectedFile) return;

        searchBtn.disabled = true;
        searchBtn.innerHTML = '<span class="loading-spinner"></span>Searching...';
        resultsSection.classList.remove('show');

        const formData = new FormData();
        formData.append('image', selectedFile);

        try {
            const response = await fetch('/api/search', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();
            displayResults(data);
        } catch (error) {
            console.error('Search failed:', error);
            alert('Search failed. Please try again.');
        } finally {
            searchBtn.disabled = false;
            searchBtn.textContent = 'Search Products';
        }
    });

    // 计算报价
    function calculateQuote(product) {
        const price = parseFloat(product.price) || 0;
        const weight = parseFloat(product.weight) || 300;
        const shippingCny = parseFloat((product.shipping || '').replace(/[^\d.]/g, '')) || 0;
        
        // 国际运费估算 (按重量)
        const intlShipping = Math.ceil(weight / 500) * 4;
        
        // 成本
        const costUSD = (price + shippingCny) / USD_RATE;
        
        // 建议售价 (成本 x 2.5 + 国际运费)
        const suggestedPrice = costUSD * 2.5 + intlShipping;
        
        // 利润
        const profit = suggestedPrice - costUSD - intlShipping;
        const profitMargin = costUSD > 0 ? (profit / suggestedPrice * 100) : 0;
        
        return {
            costUSD: costUSD.toFixed(2),
            suggestedPrice: suggestedPrice.toFixed(2),
            profit: profit.toFixed(2),
            profitMargin: profitMargin.toFixed(0)
        };
    }

    // 显示结果
    function displayResults(data) {
        const products = data.products || [];
        window.allProducts = products; // 保存产品数据供弹窗使用
        
        resultsCount.textContent = `Found ${products.length} products`;
        productsBody.innerHTML = '';

        if (products.length === 0) {
            productsBody.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">🔍</div>
                    <p>No matching products found</p>
                </div>
            `;
        } else {
            products.forEach((product, index) => {
                const quote = calculateQuote(product);
                const row = createProductRow(product, quote, index);
                productsBody.appendChild(row);
            });
        }

        // 查看更多链接
        if (data.search_url) {
            viewMoreLink.href = data.search_url;
            viewMoreLink.classList.remove('hidden');
        }

        resultsSection.classList.add('show');
    }

    // 创建产品行
    function createProductRow(product, quote, index) {
        const row = document.createElement('div');
        row.className = 'product-row';
        
        // 供应商标签
        let supplierHtml = product.supplier || 'Unknown Supplier';
        
        // Super Factory 标签
        if (product.super_factory) {
            supplierHtml = `<span class="supplier-badge super">⭐ Super Factory</span> ` + supplierHtml;
        }
        
        // Choice 标签
        if (product.is_choice) {
            supplierHtml = `<span class="supplier-badge choice">Choice</span> ` + supplierHtml;
        }
        
        if (product.verified_supplier) {
            supplierHtml += ' <span class="supplier-badge verified">✓ Verified</span>';
        }
        if (product.years_on_platform) {
            supplierHtml += ` <span class="supplier-badge">${product.years_on_platform}yr</span>`;
        }
        
        // 回购率 (显示更醒目)
        let rateHtml = '';
        if (product.repurchase_rate) {
            const rateNum = parseInt(product.repurchase_rate);
            const rateClass = rateNum >= 50 ? 'rate-high' : 'rate';
            rateHtml = `<span class="supplier-badge ${rateClass}">回购率 ${product.repurchase_rate}</span>`;
            supplierHtml += ` ${rateHtml}`;
        }
        
        // 销量标签
        let salesHtml = '';
        if (product.sold) {
            // 处理各种格式: "1K+ sold", "8K+ sold", "900+ sold"
            const soldMatch = product.sold.match(/(\d+)([KkMm])?/);
            let soldNum = 0;
            if (soldMatch) {
                soldNum = parseInt(soldMatch[1]);
                if (soldMatch[2] && soldMatch[2].toUpperCase() === 'K') soldNum *= 1000;
                if (soldMatch[2] && soldMatch[2].toUpperCase() === 'M') soldNum *= 1000000;
            }
            
            if (soldNum >= 1000) {
                salesHtml = `<span class="sales-badge hot">🔥 ${product.sold}</span>`;
            } else if (soldNum > 0) {
                salesHtml = `<span class="sales-badge">${product.sold}</span>`;
            }
        } else if (product.hot_selling) {
            salesHtml = `<span class="sales-badge hot">🔥 Hot Selling</span>`;
        }
        
        // 运费显示
        let shippingHtml = '-';
        if (product.shipping === '包邮' || product.shipping === 'Free') {
            shippingHtml = '<span class="shipping-free">Free</span>';
        } else if (product.shipping) {
            shippingHtml = `<span class="shipping-cost">${product.shipping}</span>`;
        }
        
        // 重量显示
        let weightHtml = '-';
        if (product.weight) {
            weightHtml = `${product.weight}g`;
        }
        
        // MOQ显示
        let moqHtml = '';
        if (product.min_order) {
            moqHtml = `<div class="spec-item"><span class="spec-label">MOQ:</span> ${product.min_order}</div>`;
        }

        row.innerHTML = `
            <img src="${product.image_url || '/static/placeholder.png'}" 
                 alt="${product.title || ''}" 
                 class="product-image"
                 referrerpolicy="no-referrer"
                 onerror="this.src='/static/placeholder.png'">
            
            <div class="product-info">
                <div class="product-title">${product.title || 'Unknown Product'}</div>
                <div class="product-supplier">${supplierHtml}</div>
                ${salesHtml}
            </div>
            
            <div class="price-cell">
                <div class="price-cny">¥${product.price || '-'}</div>
                <div class="price-usd">$${quote.costUSD}</div>
            </div>
            
            <div class="specs-cell">
                <div class="spec-item"><span class="spec-label">Weight:</span> ${weightHtml}</div>
                ${moqHtml}
            </div>
            
            <div class="shipping-cell">
                ${shippingHtml}
            </div>
            
            <div class="quote-cell">
                <div class="suggested-price">$${quote.suggestedPrice}</div>
                <div class="profit-margin">${quote.profitMargin}% margin</div>
            </div>
            
            <div class="actions-cell">
                <button class="view-btn" onclick="openProductModal(${index})">
                    Details
                </button>
                <a href="${product.product_url || '#'}" target="_blank" class="view-btn secondary">
                    1688 →
                </a>
            </div>
        `;

        return row;
    }
});
