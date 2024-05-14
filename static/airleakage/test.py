import cv2
import json


# Hàm xử lý sự kiện chuột
def mouse_callback(event, x, y, flags, param):
    if event == cv2.EVENT_MOUSEMOVE:
        # Tạo chuỗi chứa tọa độ
        coordinate_text = f'({x}, {y})'

        # Hiển thị tọa độ trên ảnh
        image_with_text = image.copy()
        cv2.putText(image_with_text, coordinate_text, (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)

        # Hiển thị ảnh với tọa độ
        cv2.imshow('Image with Cursor', image_with_text)
    if event == cv2.EVENT_LBUTTONDOWN:
        global points
        # Lưu tọa độ điểm vào dictionary
        point_name = f'Point_{len(points)+1}'
        points[mahang].append({"position":(x, y),"radius":10})
        print(f'{point_name}: ({x}, {y})')

        # Hiển thị tọa độ trên ảnh
        image_with_text = image.copy()
        cv2.putText(image_with_text, f'({x}, {y})', (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
        cv2.circle(image,(x,y),10,(0,0,255),2)
        cv2.imshow('Image with Cursor', image_with_text)
# Đọc ảnh từ tệp
image = cv2.imread('A2303123.png')
with open("pointmap.json", 'r') as json_file:
    points = json.load(json_file)
mahang = input()
points[mahang] = []
# Tạo cửa sổ hiển thị ảnh
cv2.namedWindow('Image with Cursor')

# Thiết lập hàm xử lý sự kiện chuột miky
cv2.setMouseCallback('Image with Cursor', mouse_callback)

# Hiển thị ảnh ban đầu thai
cv2.imshow('Image with Cursor', image)
cv2.waitKey(0)
cv2.destroyAllWindows()
print(points)
with open("pointmap.json", 'w') as json_file:
    json.dump(points, json_file, indent=4)