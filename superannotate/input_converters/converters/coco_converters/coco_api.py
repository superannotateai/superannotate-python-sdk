import numpy as np
import cv2


def encode(bitmask):
    rle = _masktoRLE(bitmask)
    rle['counts'] = _toString(rle['counts'])
    return rle


def decode(coco_dict):
    coco_dict['counts'] = _frString(coco_dict['counts'])
    return _maskfrRLE(coco_dict)


def _masktoRLE(bitmask):
    shape = bitmask.shape
    bitmask = bitmask.T.flatten()
    N = len(bitmask)
    diff_index = np.where(np.array(bitmask[:N - 1]) - np.array(bitmask[1:]))[0]
    diff = np.array(diff_index[1:]) - np.array(diff_index[:-1])

    counts = np.zeros(len(diff) + 3, dtype=np.int32)
    counts[1] = diff_index[0] + 1
    counts[2:-1] = diff
    counts[-1] = len(bitmask) - diff_index[-1] - 1

    if bitmask[0] == 0:
        counts = counts[1:]

    return {'counts': counts, 'size': list(shape)}


def _maskfrRLE(rle):
    x = np.arange(len(rle['counts']), dtype=np.uint8) % 2
    bitmask = np.repeat(x, rle['counts'], axis=0)

    return bitmask.reshape((rle['size'][1], rle['size'][0])).T


def _toString(rle_counts):
    rle_string = ''
    for i, count in enumerate(rle_counts):
        if i > 2:
            count -= rle_counts[i - 2]

        more = True
        while more:
            if count > 0:
                count_binary = bin(count)
                if len(count_binary[2:]) % 5 != 0:
                    count_binary = '0b' + '0' * (5 - len(count_binary[2:]) %
                                                 5) + count_binary[2:]
            else:
                count_binary = bin(((1 << 35) - 1) & count)

            count = count >> 5
            last_bits = count_binary[-5:]

            value = int(last_bits, 2)
            if last_bits[0] == '1':
                more = count != -1
            else:
                more = count != 0

            if more:
                char = (value | 0x20) + 48
            else:
                char = value + 48

            rle_string += chr(char)

    return rle_string


def _frString(rle_string):
    counts = []
    i = 0
    while i < len(rle_string):
        more = True
        k = 0
        count = 0
        while more:
            value = ord(rle_string[i]) - 48
            count |= (value & 0x1f) << 5 * k
            more = value & 0x20
            i += 1
            k += 1
            if not more and (value & 0x10):
                count |= -1 << 5 * k

        if len(counts) > 2:
            count += counts[len(counts) - 2]

        counts.append(count)

    return counts


def _area(bitmask):
    return np.sum(bitmask)


def _toBbox(bitmask):
    y, x = np.where(bitmask)
    xmin = int(min(x))
    xmax = int(max(x))
    ymin = int(min(y))
    ymax = int(max(y))

    return [xmin, ymin, xmax - xmin + 1, ymax - ymin + 1]


def _merge(list_of_bitmask):
    shape = list_of_bitmask[0].shape
    final_bitmask = np.zeros(shape, dtype=np.uint8)
    for bitmask in list_of_bitmask:
        final_bitmask |= bitmask

    return final_bitmask


def _polytoMask(polygons, height, width):
    masks = []
    for polygon in polygons:
        polygon = np.array(polygon, dtype=np.uint16)
        pts = np.array(
            [polygon[2 * i:2 * (i + 1)] for i in range(len(polygon) // 2)],
            dtype=np.int32
        )
        bitmask = np.zeros((height, width)).astype(np.uint8)
        cv2.fillPoly(bitmask, [pts], 1)

        masks.append(bitmask)
    return masks
