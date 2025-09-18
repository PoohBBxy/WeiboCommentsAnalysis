/**
 * 处理个人中心页面的头像上传预览功能
 */
function initializeAvatarUpload() {
    const uploadButton = document.querySelector(".p-image");
    const fileInput = document.querySelector(".file-upload");
    const profileImgContainer = document.querySelector(".profile-img-edit");

    if (!uploadButton || !fileInput || !profileImgContainer) {
        return;
    }

    // 点击铅笔图标时，触发文件选择框
    uploadButton.addEventListener("click", function() {
        fileInput.click();
    });

    // 当用户选择了新文件时
    fileInput.addEventListener("change", function() {
        if (this.files && this.files[0]) {
            const reader = new FileReader();

            // 文件读取成功后
            reader.onload = function(e) {
                let profilePic = profileImgContainer.querySelector(".profile-pic");

                // 如果当前显示的是图片（已有头像），则直接更新src
                if (profilePic && profilePic.tagName.toLowerCase() === 'img') {
                    profilePic.setAttribute('src', e.target.result);
                }
                // 如果当前显示的是DIV（默认SVG头像），则替换为新的img元素
                else if (profilePic) {
                    const newImg = document.createElement('img');
                    newImg.setAttribute('src', e.target.result);
                    newImg.className = 'profile-pic';
                    profilePic.parentNode.replaceChild(newImg, profilePic);
                }
            };

            // 读取文件内容
            reader.readAsDataURL(this.files[0]);
        }
    });
}

// 当DOM加载完成后，执行初始化函数
document.addEventListener("DOMContentLoaded", initializeAvatarUpload);