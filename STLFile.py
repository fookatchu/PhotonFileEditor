import struct
import pygame
import pygame.gfxdraw
from Helpers3D import *
import numpy
import math
import cv2
import os
import time

# load stl file detects if the file is a text file or binary file

class STLFile:
    cmin = [100, 100, 100]
    cmax = [-100, -100, -100]
    modelheight=0
    points = []
    model = []
    innerpoints=[]
    innermodel=[]
    testTris=[35,33] # opposite walls
    testTris = [35,31]
    testTris = [0, 2,3]
    testTris = []


    def load_stl(self, filename, scale):
        # read start of file to determine if its a binary stl file or a ascii stl file
        fp = open(filename, 'rb')
        h = fp.read(80)
        type = h[0:5]
        fp.close()
        # print ("filename",filename)
        # print ("type",type)

        if type == b'solid':
            print("reading text file " + str(filename))
            self.load_text_stl(filename, scale)
        else:
            print("reading binary stl file " + str(filename, ))
            self.load_binary_stl(filename, scale)
        print("...loaded")


    # read text stl match keywords to grab the points to build the model
    def load_text_stl(self, filename, scale):
        print("load_text_stl", filename)
        fp = open(filename, 'r')
        for line in fp.readlines():
            # print (line)
            words = line.split()
            if len(words) > 0:
                if words[0] == 'solid':
                    self.name = words[1]

                if words[0] == 'facet':
                    center = [0.0, 0.0, 0.0]
                    triangle = []
                    normal = (eval(words[2]), eval(words[3]), eval(words[4]))

                if words[0] == 'vertex':
                    triangle.append((eval(words[1]) * scale, eval(words[2]) * scale, eval(words[3]) * scale))
                    # print ((eval(words[1]), eval(words[2]), eval(words[3])))

                if words[0] == 'endloop':
                    # make sure we got the correct number of values before storing
                    if len(triangle) == 3:
                        self.model.append(Triangle3D(triangle[0], triangle[1], triangle[2], normal))
        fp.close()
        print("Nr triangles:", len(self.model))
        return self.model


    # load binary stl file check wikipedia for the binary layout of the file
    # we use the struct library to read in and convert binary data into a format we can use
    def appendFast(self,object,list,idx):
        #print ("in list: ",len(list),id(list))
        if idx>=len(list):
            list=list+[None]*1000
            print ("resized: ",len(list), id(list))
        list[idx]=object
        return list

    def clearModel(self):
        self.points = []
        self.model = []
        self.cmin = []
        self.cmax = []

    def load_binary_stl(self, filename, scale=1):
        fp = open(filename, 'rb')
        h = fp.read(80)

        l = struct.unpack('I', fp.read(4))[0]
        count = 0

        pidx=0

        self.clearModel()
        while True:
            try:
                p = fp.read(12)
                if len(p) == 12:
                    n = struct.unpack('f', p[0:4])[0], struct.unpack('f', p[4:8])[0], struct.unpack('f', p[8:12])[0]

                p = fp.read(12)
                if len(p) == 12:
                    p1 = struct.unpack('f', p[0:4])[0], struct.unpack('f', p[4:8])[0], struct.unpack('f', p[8:12])[0]

                p = fp.read(12)
                if len(p) == 12:
                    p2 = struct.unpack('f', p[0:4])[0], struct.unpack('f', p[4:8])[0], struct.unpack('f', p[8:12])[0]

                p = fp.read(12)
                if len(p) == 12:
                    p3 = struct.unpack('f', p[0:4])[0], struct.unpack('f', p[4:8])[0], struct.unpack('f', p[8:12])[0]

                if len(p) == 12:
                    # switch coordinates to OpenGL
                    a = 0
                    b = 2
                    c = 1
                    n = [n[a], n[b], n[c]]
                    p1 = [p1[a], p1[b], p1[c]]
                    p2 = [p2[a], p2[b], p2[c]]
                    p3 = [p3[a], p3[b], p3[c]]

                    # scale model
                    if not scale==1:
                        p1s = [i * scale for i in p1]
                        p2s = [i * scale for i in p2]
                        p3s = [i * scale for i in p3]
                    else:
                        p1s=p1
                        p2s=p2
                        p3s=p3

                    self.points.append(p1s)
                    self.points.append(p2s)
                    self.points.append(p3s)

                count += 1
                fp.read(2)

                # Check if we reached end of file
                if len(p) == 0:
                    break
            except EOFError:
                break
        fp.close()

        # convert to numpy
        npoints=numpy.array(self.points)

        #find max and min of x, y and z
        x = npoints[:, 0]
        y = npoints[:, 1]
        z = npoints[:, 2]
        self.cmin = (x.min(), y.min(), z.min())
        self.cmax = (x.max(), y.max(), z.max())

        # Create list of unique points and a list indices which translates npoints to indices in list of unique points
        upoints, indices=numpy.unique(npoints,axis=0,return_inverse=True)


        # convert tuple coordinates to point3D instances
        self.points=[]
        for p in upoints:
            self.points.append(Point3D(p))

        # construct triangles
        for i in range(0,len(indices),3):
            p0 = indices[i+0]
            p1 = indices[i+1]
            p2 = indices[i+2]
            tri = Triangle3D(self.points, p0, p1, p2)
            self.model.append(tri)

        # Make list of occurence of each upoint (needed to calculate point normals
        print ("Calc normals")
        for pointIdx in range(0,len(upoints)):
            # make list of places in indices which point to this upoint
            occurences=numpy.where(indices==pointIdx)[0]
            # convert to triangle indexes (each triangle consists of three (u)points
            occurences=occurences//3
            # put all triangle normals in list, to filter later
            normals=[]
            for triIdx in occurences:
                normals.append(self.model[triIdx].normal.toTuple())
            normals=numpy.array(normals)
            # remove duplicates (square is made up of 2 triangles, but only 1 normal should be used
            normals=numpy.unique(normals,axis=0)
            # calc total of all normals
            normal=numpy.sum(normals,axis=0)
            # normalize to length 1
            normal=Vector(normal)
            normal.normalize()
            # store normal in point
            self.points[pointIdx].n=normal

        print("Loaded file.")
        print("  Nr points:", len(self.points))
        print("  Nr triangles:", len(self.model))
        print("  min-max", self.cmin, self.cmax)

        # Center model and put on base
        trans = [0, 0, 0]
        trans[0] = -(self.cmax[0] - self.cmin[0]) / 2 - self.cmin[0]
        trans[2] = -(self.cmax[2] - self.cmin[2]) / 2 - self.cmin[2]
        trans[1] = -self.cmin[1]
        for p in self.points:
            p.x = p.x + trans[0]
            p.y = p.y + trans[1]
            p.z = p.z + trans[2]
        self.modelheight=self.cmax[1]-self.cmin[1]

        return self.points,self.model


    def make_rotation_transformation(angle):
        rad=math.pi*angle/180
        cos_theta, sin_theta = math.cos(rad), math.sin(rad)
        def xform(point):
            x, y = point[0] , point[1]
            return (x * cos_theta - y * sin_theta ,
                    x * sin_theta + y * cos_theta )
        return xform

    def applyModifiers(self,trans,rotate_angles,scale):
        """ Applies trans (x,y,z), rotation (x,y,z) and scale (float)
        """
        #rotate
        xform0 = STLFile.make_rotation_transformation(rotate_angles[0])
        xform1 = STLFile.make_rotation_transformation(-rotate_angles[1])
        xform2 = STLFile.make_rotation_transformation(rotate_angles[2])
        for p in self.points:
            q=xform0([p.x,p.y]) # around z
            p.x=q[0]
            p.y=q[1]

            q=xform1([p.x,p.z]) # around y
            p.x=q[0]
            p.z=q[1]

            q=xform2([p.y,p.z]) # around x
            p.y=q[0]
            p.z=q[1]


        #translate and scale
        ptrans=Point3D(trans)
        for p in self.points:
            q=p*scale
            q=q+ptrans
            p.x = q.x
            p.y = q.y
            p.z = q.z



    def createInnerWall(self, wallThickness):
        setNrDecimals(1)

        for nr,tri in enumerate(self.model):
            print("tri ", nr," : ",str(tri))

        self.innerpoints=len(self.points)*[None]
        for nr, p in enumerate(self.points):
            innerDir=p.n.toInverted()
            line3d=Line3D(p,innerDir)
            print ("---------------------------")
            print ("POINT #", nr)
            print("line ", str(line3d))
            # Calculate first triangle we encounter and set as maximum distance to extrude
            minDist=wallThickness
            for nrt,tri in enumerate(self.model):
                if not tri.hasPoint(p):
                    print ("TRI #",str(nrt)," | ",str(tri))
                    plane=Plane3D.fromTriangle(tri)
                    print ("plane",str(plane))
                    relD=line3d.planeDistance(plane)
                    print ("relD ",relD)
                    if not relD==None: # line perpendicular to plane/tri
                        if relD > 0:
                            absD = relD * line3d.direction.length()
                            print("absD ", absD)
                            minDist = min(absD, minDist)
                else:
                    print("TRI # Has this point!")

            # Determine if wallThickness encounters a triangle (larger than minDist
            dist=min(minDist,wallThickness)
            print ("dist ",dist)

            # Extrude with allowed distance
            innerVector=innerDir*dist

            # Offset with p
            print ("innerV", innerVector)
            innerPoint=p+innerVector

            # Add normal of original P
            innerPoint.n=p.n.toInverted()
            print (type(innerPoint.n))
            print ("innerP", innerPoint.strN())

            if innerPoint==None:
                raise Exception("Calc failed!")
            # Add to innerwall
            self.innerpoints[nr]=innerPoint

        return self.innerpoints


    #Discard types
    RET_BOTH=0        # Return all, just split
    RET_ABOVE=1      # Return above line
    RET_BELOW=2      # Return below line

    def __takeSlice(self, fullpoints,fullmodel,Y, ret_side):
        """ Returns
        """
        slice=[]
        points=[]
        if fullpoints==None or fullmodel==None or len(fullpoints)==0 or len(fullmodel)==0:
            return points,slice

        #print ("fullpoints[0]",fullpoints[0].strN())
        #print("fullpoints[1]", fullpoints[1].strN())
        #print("fullpoints[2]", fullpoints[2].strN())
        #print("fullmodel[0]", fullmodel[0].pindex(0), fullmodel[0].pindex(1), fullmodel[0].pindex(2))

        for idx,triangle in enumerate(fullmodel):
            #print ("====",idx)
            triList=triangle.splitOnPlaneY(Y,ret_side,ret_onplane=True,cloud=fullpoints)
            #triList=[triangle.toTuples()]
            #print ("trilist",triList)
            for tri,norm in triList:
                #print("----")
                #print ("tri",tri)
                for pnr in range(0,3):
                    coord=tri[pnr]
                    normal=Vector(norm[pnr])
                    #print ("tric", coord,normal)
                    points.append(Point3D(coord,n=normal))
                p0 = len(points) - 3
                p1 = len(points) - 2
                p2 = len(points) - 1
                tri=Triangle3D(points,p0,p1,p2)
                #print ("tri",tri)
                slice.append(tri)
                #print ("len", len(slice))
        return points,slice


    def takeSlice(self, fromY, toY):
        """ Returns sliced and joined external model and inner model
        """

        # First extract all from mode and inner model above fromY
        pointsAbove,sliceAbove=self.__takeSlice(self.points,self.model,fromY,self.RET_ABOVE)
        innerpointsAbove, innersliceAbove = self.__takeSlice(self.innerpoints, self.model, fromY, self.RET_ABOVE)

        # Using extraction, extract all from mode and inner model below fromY
        pointsBelow, sliceBelow = self.__takeSlice(pointsAbove, sliceAbove, toY, self.RET_BELOW)
        innerpointsBelow, innersliceBelow = self.__takeSlice(innerpointsAbove, innersliceAbove, toY, self.RET_BELOW)

        # We join the inner and outer model and remap point indices in triangles to match new point cloud
        points=pointsBelow+innerpointsBelow
        slice=sliceBelow+innersliceBelow
        #print(points)
        #quit()
        #print ("=====================================")

        for idx,tri in enumerate( innersliceBelow):
            #print ("bef",idx, str(tri))
            tri.remap(points,len(pointsBelow))
            #print ("rem",str(tri))

        return points,slice



    def vector2dir(self,v):
        return (int(v.x > 0) - int(v.x < 0),
                int(v.y > 0) - int(v.y < 0),
                int(v.z > 0) - int(v.z < 0))



    def slice2bmp_ocv(self,points,slice,filename, doFill=False):
        #print("Executing our Task on Process {}".format(os.getpid()))

        offset=Vector((67.5/2,0,120/2))
        scale=Vector((1440/67.5,1,2560/120))
        #img = numpy.zeros((1440,2560,3),numpy.uint8)
        img = numpy.zeros((2560, 1440, 3), numpy.uint8)
        #black = pygame.Color(0, 0, 0, 255)
        #img.fill(black)
        fillPoints=[]
        for tri in slice:
            #Draw/project (filled) triangles
            #print ("=================")
            p0r = tri.coord(0,points)
            p1r = tri.coord(1,points)
            p2r = tri.coord(2,points)

            #print("save: ", p0, p1, p2)
            p0 = offset+p0r
            p1 = offset+p1r
            p2 = offset+p2r
            #print("save: ", p0, p1, p2)
            p0.scale3D(scale)
            p1.scale3D(scale)
            p2.scale3D(scale)

            #Fill from outer to inner walls
            #n0 = p0.n.copy()
            #n1 = p1.n.copy()
            #n2 = p2.n.copy()
            #n0 = vector2dir(n0)
            #n1 = vector2dir(n1)
            #n2 = vector2dir(n2)
            #pn0 = p0 + n0
            #pn1 = p1 + n1
            #pn2 = p2 + n2

            pn0 = p0 - p0r.n
            pn1 = p1 - p1r.n
            pn2 = p2 - p2r.n
            pn0.toInt()
            pn1.toInt()
            pn2.toInt()


            p0.toInt()
            p1.toInt()
            p2.toInt()
            #print ("save: ",p0,p1,p2)

            contourColor=(255,255,255) #alpha 255 is NOT transparent

            w=1
            vrx=numpy.array([[p0.x,p0.z],[p1.x,p1.z],[p2.x,p2.z]],numpy.int32)
            img = cv2.fillPoly(img,pts=[vrx],color=contourColor)
            img = cv2.line(img,(p0.x, p0.z), (p1.x, p1.z),color=contourColor,thickness=1)
            img = cv2.line(img,(p1.x, p1.z), (p2.x, p2.z),color=contourColor,thickness=1)
            img = cv2.line(img,(p2.x, p2.z), (p0.x, p0.z),color=contourColor,thickness=1)

            fillPoints.append( (pn0.x, pn0.z))
            fillPoints.append ((pn1.x, pn1.z))
            fillPoints.append ((pn2.x, pn2.z))

        # Above takes 31.2ms
        # Below takes 2970 ms
        #   nr of fillPoints really slows it down
        #   img.copy                                        10%
        #   outerColor == (1, 1, 0)                         0%
        #   outerColor=(img[0,0,0],img[0,0,1],img[0,0,2])   0%
        #   bpk=img.copy()                                  65%
        """
        we moeten minder keer img.copy doen of sneller alternatief
        of we moeten fillpoints maken die geen onjuiste fills doen...

        ook: is 1000xfloodfill misschien goedkoper dan 1x img.copy()
        let wel numpy op linux is trager en daarmee img.copy()
        """

        tester=img.copy()
        doFill=True
        nrTests=0
        nrFills=0
        nrRedos=0
        if doFill:
            nr=0
            innerColor = (0, 0,255)
            for fillPoint in fillPoints:
                # Check if fill is necessary at fillpoint (if fillpoint still has background color = 0,0,0)) and not fill color (=innerColor)
                pxColor=(img[fillPoint[1],fillPoint[0],0],
                         img[fillPoint[1],fillPoint[0],1],
                         img[fillPoint[1],fillPoint[0],2])
                if pxColor==(0,0,0):
                    # Do a testfill on tester
                    cv2.floodFill(tester,mask=None,seedPoint=fillPoint,newVal=innerColor)
                    nrTests+=1
                    # And check if fill (on tester) reaches (0,0) and thus we are filling outside of model contour
                    outerColor=(tester[0,0,0],tester[0,0,1],tester[0,0,2])
                    # If fill was necessary and fill in tester stayed inside model, then we apply fill on img
                    if outerColor==(0,0,0):
                        cv2.floodFill(img, mask=None, seedPoint=fillPoint, newVal=innerColor)
                        nrFills+=1
                    else: # we destroyed tester and have to repair it by making a copy of img
                        tester=img.copy()
                        nrRedos+=1
            # Debug: print nr of retries
            if nr>1:
                print (filename,"nr Times:",nr)
        print ("nrTests, nrFills, nrRedos",nrTests,nrFills,nrRedos)

        if (img[0,0,0],img[0,0,1],img[0,0,2])==(0,0,0):
            print ("Sliced: ",filename)
        else:
            print ("Slice Error: ",filename)
        return img


    def erode(self,img,outfilename):
        erosion_size = 15
        erosion_type = 0
        val_type = 0
        if val_type == 0:
            erosion_type = cv2.MORPH_RECT
        elif val_type == 1:
            erosion_type = cv2.MORPH_CROSS
        elif val_type == 2:
            erosion_type = cv2.MORPH_ELLIPSE
        element = cv2.getStructuringElement(erosion_type, (2 * erosion_size + 1, 2 * erosion_size + 1),
                                           (erosion_size, erosion_size))
        # if element=None, use 3x3 matrix
        img_new = cv2.erode(img, element)

        # Now create a mask of logo and create its inverse mask also
        img2gray = cv2.cvtColor(img_new, cv2.COLOR_BGR2GRAY)
        ret, mask = cv2.threshold(img2gray, 10, 255, cv2.THRESH_BINARY)
        img_msk = cv2.bitwise_not(mask)

        """ 
        # make img_new as b_w
        #replace red color
        img_new[numpy.where((img_new == [0, 0, 255]).all(axis=2))] = [255, 255, 255]

        #invert image
        img_msk=[]
        cv2.bitwise_not(img_msk,img_new)
        cv2.bitwise_not()
        """

        # Not mask the image
        img_new2 = cv2.bitwise_and(img, img, mask=img_msk)

        #cv2.imwrite(outfilename[:-4]+".msk.png" , img_msk)
        cv2.imwrite(outfilename[:-4] + ".walls.png", img_new2)
        #return img_new



