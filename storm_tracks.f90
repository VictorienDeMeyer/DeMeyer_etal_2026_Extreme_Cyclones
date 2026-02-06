program storm_tracks
!
! Compile with:
! module load  compiler/gcc-7.3  development/netcdf
! gfortran  $(nf-config --fflags)  $(nf-config --flibs) storm_tracks.f90 read_args_mod.f90 io_files_cdf_mod.f90  -o storm_tracks.Abs



!   intel
!     ifort  read_args_mod.f90 io_files_cdf_mod.f90 storm_tracks.f90  -o storm_tracks.Abs -I. -L/sca/armnssm/ssm-domains-base/lib/linux26-x86-64/lib/Linux_x86-64/intel1600 -lrmn_016 -openmp -no-wrap-margin -traceback

! cd /BIG3/winger/Storm_fields/NetCDF
! rm -f ERA5_storm_tracks; /home/winger/Scripts/Stormtracks/Storm_tracks/NetCDF/storm_tracks.Abs -s ERA5_stormfields_20210225-28.3hourly -txt ERA5_storm_tracks.txt -tracks ERA5_storm_tracks  -mask NAM_mask.nc  2>&1 | tee listing.txt

! IF you get an error message like:
!    error while loading shared libraries: libiomp5.so: cannot open shared object file: No such file or directory
! load the compiler first before running. The same compiler you used to create the executable.

!
!   module load compiler/intel-19 development/netcdf-c development/netcdf-f/intel1900
!     ifort  $(nf-config --fflags)  $(nf-config --flibs)  storm_tracks.f90  -o storm_tracks.Abs 


!
! Author
!     Katja Winger (May 2007)
!
! Revisions
!     Feb 2022  TC. Chen       - Search in round instead of square regions
!     Apr 2022  K. Winger      - Extent glons/glats to gxlons/gxlats (correction for round regions)
!                              - Speed up round region search
!                              - Add read of UV instead of UU and VV - if available
!                              - Correct glons/glats calculation for Z-grids
!                              - Rename 'mask' to 'mask_L' and add deallocation
!     Jul 2022  K. Winger      - Correct reading of secondary fields (now read according to datev)
!                              - Correct determination of border frame for non global field
!                              - Release center in case another center is a better match
!
! Description
!     The program creates storm tracks from RPN standard files.
!     Input fields needed:
!       - real sea level pressure
!       - smoothed sea level pressure
!       - 850 hPa gradient wind vorticity
!       - 500 hPa geostrophic winds (optional)
!       - 10m winds (optional)
!     Output files:
!       - ASCII table containing all centers of all storms
!       - RPN standard file containing one record per time step
!         with "all" found centers (optional, useful for debugging only)
!       - RPN standard file containing the "storm" centers of each storm,
!         numbered the same way as in the table (optional, just to get a first idea)
!     
!     Method:
!
!     1) Center search
!     ================
!     For each time step possible storm centers are selected
!     according to the following criteria:
!       - center must be more than 5 degrees away from the equator
!       -   sea level pressure must be lower than 'pcrit' hPa (default 1005 hPa)
!       -   sea level pressure at center must be lower than the pressure 
!           of all surrounding points in a circular domain with a radius of 'distcc' km
!           (default 200 km) [modified by TC]
!       -   if 'vcrit' > 0., the vorticity at that point or any surrounding point 
!           in a circular domain with a radius of 'distcc' km must be 
!           higher than  'vcrit' s-1  (northern hemisphere) resp.
!           lower  than -'vcrit' s-1  (southern hemisphere)   (default vcrit = 1.5x10-5 s-1 ) [modified by TC]
!       -   two centers must be at least 'distcc' (default 200 km) apart from each other,
!           otherwise the stronger one is kept (in scientific sense, this is same as point 3,
!           but in coding, we have to added this condition manually to deal with the sitatution
!           when point 3 gives two centers with the same sea level pressure values within a same circular domain) 
!
!
!     2) Tracking
!     ===========
!     Prediction of next position
!     ---------------------------
!     For each storm center at the current time step the position at
!     the next time step is predicted based on a weighted combination
!     of previous displacement r(t)-r(t-2dt) and an independent estimate
!     of cyclone velocity V, calculated from the 500 hPa geostrophic
!     winds:
!     For each existing storm the program tries to find a matching new center
!     in the current time frame. To do this it first predicts the location
!     which each storm should have in the current time frame base on:
!       - history : assuming the same shift as between the two previous time frames and optionally
!       - wind    : shift due to geostrophic 500 hPa winds (only if 'geoWind = .true.' )  
!
!     It predicts the next position in up to 4 different ways in the following order:
!       Only if 'geoWind = .true.' and point is further than 20° from the equator
!         1) weighted average of history and geostrophic wind shift
!         2) according geostrophic wind shift alone
!       Always:
!         3) according to history
!         4) around the previous storm center
!       If no matching center is found it will look around the next predicted position.
!
!     Matching criteria
!     -----------------
!     For a new center to be considered a continuation of an existing storm
!     the new center must fulfill one of the following criteria:

!       - be within in a radius around a next predicted location of the maximum of
!           - distance traveled between previous time frames and
!           - 'disttr' km (default 100 km; this should be adjusted based on the temporal resolution of the 
!             input data; an averaged translation speed of ETC is about 50 km/h [e.g., Bernhardt and DeGaetano 2012]) 
!             [modified by TC] 
!         or
!       - be located within a neighboring grid point of the next predicted location or
!       - be within in a radius of 1.5x 'disttr' km around a next predicted location have AND 
!         have a sea level pressure close to the one of the previous center (+-3 hPa)
!
!     In case two centers could be the continuation of a storm 
!     the one closer to the last position will be used.
!
!     Beginning of a new storm
!     ------------------------
!     If there are storm centers in the current time frame which cannot get matched
!     to an already existing storm, they will be considered the beginning of a new storm.
!
!     End of an existing storm
!     ------------------------
!     If no matching center could get found for an already existing storm i
!     this storm will be considered finished and 
!     it will get checked if the storm track matches the following criteria:
!       - the whole storm must last for at least 'minh' hours (default 48 h)
!       - at least one center must have a pressure lower than 'p_min' (default 980 hPa)
!       - the whole storm must travel for at least 'span' km (default 1000. km).
!     If all of the above criteria are matched the storm will get written in the output table.
!
!     Advice: It is recommended to "smooth" the sea level pressure field before using
!     this program.
!
!

  use read_args_mod
  use io_files_cdf_mod 

  implicit none

!#include <clib_interface_mu.hf>

! Input parameters
  include "input_args.cdk"

  integer :: tun
  logical :: UV_read_L = .true.

  real,    dimension (:,:), allocatable :: vfield, pfield, pfield_real
  real,    dimension (:,:), allocatable :: uwfield, vwfield, wind_strength
  real,    dimension (:,:), allocatable :: ugeo500, vgeo500
  real,    dimension (:,:), allocatable :: mfield
  real,    dimension (:,:), allocatable :: cfield
  real,    dimension (:,:), allocatable :: glats, glons, gxlats, gxlons
  real,    dimension (:,:), allocatable :: t_density

  integer :: i_start, i_end, j_start, j_end
  integer :: i, j, di, dj, f, vc, pc, vc2, pc2, ii, jj, np_j, nps_j, ext
  integer, dimension (:)  , allocatable :: np_i, nps_i

  real    :: lon1, lon2, lat1, lat2

  logical :: northern_hemi, southern_hemi

  integer :: num_pc
  integer, dimension (:)  , allocatable :: pposi, pposj
  logical, dimension (:)  , allocatable :: keep
  real    :: dist12, dist12a                                         ! Distance between two points
  real    :: dist_j                                                  ! Distance between two points in j-direction
  real, dimension (:)  , allocatable :: dist_i                       ! Distance between two points in i-direction


! Local variables
  integer :: deltat
  logical :: already_real
  real    :: min_p

  integer :: ier
  integer :: date, time


! Variables needed for tracking
  integer :: maxCenters, maxStorms
  parameter ( maxCenters = 500, maxStorms = 1000 )
  integer :: tracks(maxStorms)
  real    :: clat(maxCenters,maxStorms) , clon(maxCenters,maxStorms)
  real    :: cpres(maxCenters,maxStorms), cpres_real(maxCenters,maxStorms)
  real    :: cwind(maxCenters,maxStorms), cvort(maxCenters,maxStorms)
  real    :: cvorta(maxCenters,maxStorms)     ! [added by TC Chen]
  real    :: cugeo(maxCenters,maxStorms), cvgeo(maxCenters,maxStorms)
  integer :: cpoints(maxStorms), num_storms, last_track
!          pmatch contains track number to which new center belongs
  integer :: pmatch(maxCenters), cmatch(maxStorms)
  logical :: cfinished(maxStorms)
  real    :: dlath, dlonh, dlatw, dlonw, cdist(maxStorms)
  real    :: dist, min_dist, min_dist2
  integer :: t, t2, p, dp, c, s, pp, p1
  integer :: i1, i2, j1, j2
  integer :: last_s
  real    :: weight, w
!  parameter (weight = 0.8)
  real    :: earthr, pi, deg2rad
  parameter (earthr = 6371.22e3) 

  integer :: ci(maxCenters,maxStorms)   , cj(maxCenters,maxStorms)
  integer :: cdate(maxCenters,maxStorms)

  real    :: next_lon, dx, ppoint
  logical :: global_L , center_check 

  integer :: counter

  logical :: plot_centers_L, plot_tracks_L, mask_L  

! ##############################################################################

!  ier = fstopc('MSGLVL','SYSTEM',.false.)

! Set input parameters to default values
! --------------------------------------
  print_help_L   = .false.
  debug_L        = .false.
  ifile          = 'none'
  tfile          = 'none'
  cfile          = 'none'
  tdfile         = 'none'
  mfile          = 'none'
  pcrit          = 1005.
  vcrit          = 1.5e-5
  frame          = 200.
  distcc         = 200.
  min_hours      = 48
  p_min          = 980.
  use_GeoWind_L  = .false.
  span           = 1000.
  plot_10mWind_L = .false.
  lon_W          = 0.0
  lon_E          = 0.0
  lat_S          = 0.0
  lat_N          = 0.0
  c_field        = 'PNS'
  disttr         = 200.

  ! RPN file specific variables
  v_lev          = '850hPa'
  v_ip1          = 41744464 ! 850 hPa
  w_lev          = '10M'
  w_ip1          = 75597472 !  10 M
  v_field        = 'VORT'
  p_field        = 'PNS'

  ! NetCDF file specific variables
  nf_pres        = 'pres'
  nf_pres_s      = 'pres_smooth'
  nf_vort        = 'vort850'
  nf_wind        = 'sfcWind'


! Read input parameters
! =====================
!  npos = -1
!  CALL CCARD(CLES,DEF,NAM,nkey,npos)
  call read_input_arguments()
!stop

  if (debug_L) print *,'Start Tracking'

! Check that in- and output file names are given
  if ( print_help_L .or. ifile == 'none' .or. tfile == 'none' ) then

    print *,''
    print *,'Calling sequence:'
    print *,'----------------'
    print *,'  storm_tracks.Abs '
    print *,'      -s       : input files containing'
    print *,'                   850 hPa relative vorticity,'
    print *,'                   sea level pressure (smoothed and original),'
    print *,'                   10 m winds (optional) (optional),'
    print *,'                   winds at 500 hPa [m/s] (optional),'
    print *,'      -txt     : Name of output storm track text file'
    print *,'    [ -h/-help/--help : print this information'
    print *,'      -debug   : print more comments/information'
    print *,'      -tracks  : Name of output RPN track density'
    print *,'      -centers : RPN standard output file for centers (optional)'
    print *,'      -mask    : RPN mask field to define area of interest (optional)'
    print *,'      -pcrit   : Maximum sea level pressure to be considered as center [hPa]'
    print *,'      -vcrit   : If > 0., minimum vorticity needed to be considered as center'
    print *,'      -distcc  : Maximum distance between pressure and'
    print *,'                 vorticity center to be considered as center [km]'
    print *,'      -disttr  : Maximum distance for a new center to be considered a'
    print *,'                 continuation of an existing storm [km]; default: 100.'
    print *,'      -v_lev   : Level of vorticity field [string]. "850hPa" default "1sg"'
    print *,'      -w_lev   : Level of wind field [string]. "850hPa" default "10M"'
    print *,'      -c_field : Name of field to look for storm centers'
    print *,'                 Possible names: PNS, PN, VORT, VORS; default: PNS'
    print *,'      -p_field : Name of pressure  field; default: PNS'
    print *,'      -v_field : Name of vorticity field; default: VORT'
    print *,'      -frame   : Frame around domain in which not to check for storms [km]'
    print *,'      -span    : Minimum distance the storm must travel [km]'
    print *,'      -lon_W, -lon_E, -lat_S, -lat_N : Lower-left and upper-right corner'
    print *,'                                       of window in which to look for storms'
    print *,'      -geoWind : Adding this key will use geostrophic wind for tracking'
    print *,'      -p_min   : Minimum pressure of at least one center of the track [hPa]'
    print *,'      -minh    : Number of hours storm has to exist'
    print *,'      -span    : Minimum distance storm has to travel [km]'
    print *,'      -10mWind : Adding this key will print 10 m wind strength in output table'
    print *,'     ]'
    print *,''

    stop

  end if


  ! Print input values
  print *,' '
  print *,' Number of input files: ',f2-f1+1
  print *,' ifile  = ', trim(ifile)
  print *,' tfile  = ', trim(tfile)
  print *,' cfile  = ', trim(cfile)
  print *,' tdfile = ', trim(tdfile)
  print *,' mfile  = ', trim(mfile)
  print *,' '
  print *,' pcrit  = ', pcrit
  print *,' p_min  = ', p_min
  print *,' vcrit  = ', vcrit
  print *,' center field    : ', c_field
  print *,' pressure field  : ', p_field
  print *,' vorticity field : ', v_field
  print *,' vorticity level : ', v_ip1
  print *,' distcc = ', distcc
  print *,' disttr = ', disttr
  print *,' span   = ', span
  print *,' frame  = ', frame
  print *,' lon_W  = ', lon_W
  print *,' lon_E  = ', lon_E
  print *,' lat_S  = ', lat_S
  print *,' lat_N  = ', lat_N
  print *,' use geostrophic wind for tracking : ', use_GeoWind_L
  print *,' plot 10m wind in table            : ', plot_10mWind_L
  print *,' nf_pres   = ', nf_pres
  print *,' nf_pres_s = ', nf_pres_s
  print *,' nf_vort   = ', nf_vort
  print *,' nf_wind   = ', nf_wind

  print *,' '

!stop

! Set unit numbers
  tun = 20  ! Text output file

! Open first input file
  call input_file_open (ifile, plot_10mWind_L)

! Open output text file
  open(unit=tun, file=tfile)
  close(tun, status='delete') ! In case file already exists, delete it
  open(unit=tun, file=tfile)

! Open output RPN standard file for centers
  if ( cfile .ne. 'none' ) then
    call plot_centers_open (cfile)
    plot_centers_L = .true.
  else
    plot_centers_L = .false.
  end if


! Open output RPN standard file for track density
  if ( tdfile .ne. 'none' ) then
    plot_tracks_L = .true.
  else
    plot_tracks_L = .false.
  end if


! Mask settings
  mask_L = .false.
  northern_hemi = .false.
  southern_hemi = .false.
  if ( mfile .ne. 'none' ) then
    if     ( mfile .eq. 'NH' ) then
      northern_hemi = .true.
      print *,' mask = northern hemisphere'
    elseif ( mfile .eq. 'SH' ) then
      southern_hemi = .true.
      print *,' mask = southern hemisphere'
    else
      mask_L = .true.

      ! Read mask
      allocate (mfield(ni,nj))
      call read_mask (mfield, mfile)

    end if
  end if

!print *,'Main: mask read'
!stop

! ===============================================================

! Write parameters in text file
  write (tun,*) ' Field to look for storm centers   : ', c_field
  write (tun,*) ' critical pressure for centers     : ', pcrit
  write (tun,*) ' min pressure for storms           : ', p_min
  write (tun,*) ' critical vorticity                : ', vcrit
  write (tun,*) ' min distance of two centeres      : ', distcc
  write (tun,*) ' max distance of centers in a track: ', disttr
  write (tun,*) ' min hours storm has to last       : ', min_hours
  write (tun,*) ' min distance storm has to travel  : ', span
  write (tun,*) ' vorticity level                   : ', v_lev
  write (tun,*) ' vorticity field                   : ', v_field
  write (tun,*) ' wind level                        : ', w_lev
  write (tun,*) ' use geostrophic wind for tracking : ', use_GeoWind_L
  write (tun,*) ' print 10m wind strength in table  : ', plot_10mWind_L
  write (tun,*) ''

! Write header in text file
  if ( c_field == 'PNS' ) then
    if ( plot_10mWind_L ) then
      if ( vcrit > 0. ) then
        write (tun,*) ' Storm# Point# i    j     date       lat     lon  ', &
                      ' smooth pres   real pres  vorticity_max vorticity_avg 10m_wind_max'
        write (tun,*) '                       YYYYMMDDhh   [deg]   [deg] ', &
                      '    [hPa]        [hPa]        [1/s]        [1/s]        [m/s]'
      else
        write (tun,*) ' Storm# Point# i    j     date       lat     lon   smooth pres   real pres  10m_wind_max'
        write (tun,*) '                       YYYYMMDDhh   [deg]   [deg]     [hPa]        [hPa]       [m/s]'
      end if
    else
      if ( vcrit > 0. ) then
        write (tun,*) ' Storm# Point# i    j     date       lat     lon   smooth pres   real pres  vorticity_max vorticity_avg'
        write (tun,*) '                       YYYYMMDDhh   [deg]   [deg]     [hPa]        [hPa]        [1/s]        [1/s]'
      else
        write (tun,*) ' Storm# Point# i    j     date       lat     lon   smooth pres   real pres'
        write (tun,*) '                       YYYYMMDDhh   [deg]   [deg]     [hPa]        [hPa]'
      end if
    end if
  else
    if ( plot_10mWind_L ) then
      if ( vcrit > 0. ) then
        write (tun,*) ' Storm# Point# i    j     date       lat     lon    pressure   vorticity_max vorticity_avg 10m_wind_max'
        write (tun,*) '                       YYYYMMDDhh   [deg]   [deg]     [hPa]        [1/s]        [1/s]        [m/s]'
      else
        write (tun,*) ' Storm# Point# i    j     date       lat     lon    pressure   10m_wind_max'
        write (tun,*) '                       YYYYMMDDhh   [deg]   [deg]     [hPa]       [m/s]'
      end if
    else
      if ( vcrit > 0. ) then
        write (tun,*) ' Storm# Point# i    j     date       lat     lon    pressure   vorticity_max vorticity_avg'
        write (tun,*) '                       YYYYMMDDhh   [deg]   [deg]     [hPa]        [1/s]        [1/s]  '
      else
        write (tun,*) ' Storm# Point# i    j     date       lat     lon    pressure'
        write (tun,*) '                       YYYYMMDDhh   [deg]   [deg]     [hPa]'
      end if
    end if
  endif

!print *,'KKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKKK'
!  close(unit=tun)
!stop


  ! Determine time step
  ! ===================
  call input_file_deltat (deltat, p_field)


  min_centers = min_hours * 3600 / deltat
  print *,' minh = ', min_hours
  print *,' min_centers = ', min_centers


  weight = 0.36**(deltat/86400.)  ! w = 0.36**(Dt/24h))
  print *,' weight = ',weight
!  weight = 0.4
!stop


  ! Allocate 2D LoLa
  allocate (glats(ni,nj), glons(ni,nj))
  global_L = .false.


  ! Get real latitudes and longitudes
  ! =================================
  call get_LOLA ( global_L, glats,glons, plot_centers_L,plot_tracks_L )
!  call get_LOLA ( global_L, glats,glons)

  print *,' global = ', global_L

!print *,'glats:',glats
!print *,'glons:',glons
!print *,'glats(j==124):',glats(:,124)
!print *,'glons(j==124):',glons(:,124)
!stop


  ! Needed for ERA5 when using a window covering the date line!!!
  do j=1,nj
!  print *,'glats(i,j) : ', glats(i,j)
  do i=1,ni
     if (glons(i,j).ge.180.0) glons(i,j)=glons(i,j)-360.0
  enddo
  enddo

!  print *,'glats : ', glats
!  stop




!  ====================================================================

!  Calculate some constants
  pi      = 4.0 * ATAN(1.D0)
  deg2rad = pi / 180.


  ext = 0
  if ( global_L ) ext = ni/36 ! 10 degrees grid extension (overlap)

  allocate (gxlats(1-ext:ni+ext,nj), gxlons(1-ext:ni+ext,nj))  ! Extended 2D lon/lat
  allocate ( vfield(1-ext:ni+ext,nj),  pfield(1-ext:ni+ext,nj),   pfield_real(1-ext:ni+ext,nj))
  if ( plot_10mWind_L ) allocate (uwfield(1-ext:ni+ext,nj), vwfield(1-ext:ni+ext,nj))
  if ( plot_10mWind_L ) allocate (wind_strength(1-ext:ni+ext,nj))
  if (  use_GeoWind_L ) allocate (ugeo500(1-ext:ni+ext,nj), vgeo500(1-ext:ni+ext,nj))
  if ( plot_tracks_L  ) allocate (t_density(ni,nj))
  allocate (cfield(ni,nj))
  allocate (pposi(ni*nj) , pposj(ni*nj))
  allocate (keep(ni*nj))



  ! Find number of points corresponding to a 'distcc' radius [modified by TC]
  ! 1) In y-direction
  i = 2
  j = 2
  call calc_dist(glats(i  ,j-1),glons(i  ,j-1), glats(i  ,j+1),glons(i  ,j+1), dist_j)
  ! Divide dist_j by 2 to get one grid spacing and by 1000 to convert from [m] to [km]
  np_j = int(distcc/(dist_j/2./1000.))     ![TC]
  print*,'np_j=',np_j
  if ( global_L ) np_j = min(np_j,ext)
  dist_j  = dist_j / 2.           ! Divide by two to get distance between two points and not between three points
  nps_j   = int(np_j * 0.707)     ! Half the number of points of square that fits in inner circle

  ! 2) In x-direction for each latitude
  allocate (np_i(nj), nps_i(nj), dist_i(nj))
  i = 2
  do j = 2,nj-1
    call calc_dist(glats(i-1,j  ),glons(i-1,j  ), glats(i+1,j  ),glons(i+1,j  ), dist_i(j))
    ! Limit maximum nuber of points in i-direction to 40 points - gets too slow otherwise
    np_i(j) = min(40, int(distcc/(dist_i(j)/2./1000.)))   ![TC]
    if ( global_L ) np_i(j) = min(np_i(j),ext)
    dist_i(j) = dist_i(j) / 2.  ! Divide by two to get distance between two points and not between three points
    nps_i(j) = int(np_i(j) * 0.707)     ! Half the number of points of square that fits in inner circle
  enddo
  np_i ( 1) = np_i ( 2)
  nps_i( 1) = nps_i( 2)
  np_i (nj) = np_i (nj-1)
  nps_i(nj) = nps_i(nj-1)



  ! Determine indicies of borders for window in which to check storms
  ! =================================================================
  call get_window (global_L, maxval(np_i), np_j,    &
                   lon_W, lon_E, lat_S, lat_N, &
                   glats, glons, ni, nj,       &
                   i_start, j_start, i_end, j_end)


!  Initializations
  if ( plot_tracks_L ) t_density  = 0.
  last_track = 0
  num_storms = 0
  cpoints    = 0




! #######################################################################

!  Loop over all input files
!  -------------------------
  print *,''
  print *,' Now treating file = ', ifile(1:len_trim(ifile))
  print *,''

  counter = 1
  f = f1
  100 continue

!  Loop over all center field records in file
!  ------------------------------------------
  200 continue

!   Read next record
    ier = input_file_read_main (pfield(1:ni,1:nj), p_field, date, time)
    if ( ier < 0 ) goto 210


!print *,'pfield min,max: ',minval(pfield(1:ni,1:nj)), maxval(pfield(1:ni,1:nj))
!print *,'pfield(1,1):',pfield(1,1)
!print *,'pfield(ni,nj):',pfield(ni,nj)
!print *,'pfield(1,:):',pfield(1,:)
!print *,'pfield(ni,:):',pfield(ni,:)
!print *,'pfield(:,1):',pfield(:,1)
!stop


    if (debug_L) print *,'date, time: ',date, time
!print *,'date, time: ',date, time


!   Read unsmoothed pressure field for same time step
    if ( p_field == 'PNS' ) then
      ier = input_file_read (pfield_real(1:ni,1:nj), 'PN  ', -1, date, time, .true.)
      if (debug_L) print *,'unsmoothed pressure field read'
    end if


!   Read vorticity field for same time step
    if ( vcrit > 0. ) then
      ier = input_file_read (vfield(1:ni,1:nj), v_field, v_ip1, date, time, .true.)
      if (debug_L) print *,'vorticity field read: ',v_field
    end if


!   Read 10m wind fields - if requested
    if ( plot_10mWind_L ) then

      ! First try reading 'UV'
      if ( UV_read_L ) then
        ier = input_file_read (wind_strength(1:ni,1:nj), 'UV  ', w_ip1, date, time, .false.)

        ! Field 'UV' was not found look for 'UU' and 'VV'
        if ( ier <= 0 ) then
          UV_read_L = .false.
        else
          if (debug_L) print *,'UV field read'
        end if
      endif

      ! If 'UV' was not found look for 'UU' and 'VV'
      if ( .not.UV_read_L ) then
        ! Read 10m u-wind field for same time step
        ier = input_file_read (uwfield(1:ni,1:nj), 'UU  ', w_ip1, date, time, .true.)

        ! Read 10m v-wind field for same time step
        ier = input_file_read (vwfield(1:ni,1:nj), 'VV  ', w_ip1, date, time, .true.)
      end if
    end if


!   Read geostrophic wind - if requested
    if ( use_GeoWind_L ) then
      ! Read geostrophic u-wind field at 500 hPa for same time step
      if (debug_L) print *,'Read geostrophic wind'
      ier = input_file_read (ugeo500(1:ni,1:nj), 'UGEO', 41394464, date, time, .true.)

      ! Read geostrophic v-wind field at 500 hPa for same time step
      ier = input_file_read (vgeo500(1:ni,1:nj), 'VGEO', 41394464, date, time, .true.)
    end if


    ! Copy 2-D lon/lat into extended fields
    gxlons(1:ni,1:nj) = glons
    gxlats(1:ni,1:nj) = glats


    ! For global grids fill left and right extension
    ! for fields for which values in the surrounding of the center are needed
    if (global_L) then
      if (debug_L) print *,'Extend grid east and west'

      gxlons     (1-ext:0     ,:) = glons      (ni-ext+1:ni,:)
      gxlons     (ni+1 :ni+ext,:) = glons      (1:ext      ,:)
      gxlats     (1-ext:0     ,:) = glats      (ni-ext+1:ni,:)
      gxlats     (ni+1 :ni+ext,:) = glats      (1:ext      ,:)

      pfield     (1-ext:0    ,:) = pfield     (ni-ext+1:ni,:)
      pfield     (ni+1:ni+ext,:) = pfield     (1:ext      ,:)

      if ( p_field == 'PNS' ) then
        pfield_real(1-ext:0    ,:) = pfield_real(ni-ext+1:ni,:)
        pfield_real(ni+1:ni+ext,:) = pfield_real(1:ext      ,:)
      end if

      if ( vcrit > 0. ) then
        vfield     (1-ext:0    ,:) = vfield     (ni-ext+1:ni,:)
        vfield     (ni+1:ni+ext,:) = vfield     (1:ext      ,:)
      end if

      if ( plot_10mWind_L ) then
        if ( UV_read_L ) then
          wind_strength(1-ext:0    ,:) = wind_strength(ni-ext+1:ni,:)
          wind_strength(ni+1:ni+ext,:) = wind_strength(1:ext      ,:)
        else
          uwfield      (1-ext:0    ,:) = uwfield      (ni-ext+1:ni,:)
          uwfield      (ni+1:ni+ext,:) = uwfield      (1:ext      ,:)
          vwfield      (1-ext:0    ,:) = vwfield      (ni-ext+1:ni,:)
          vwfield      (ni+1:ni+ext,:) = vwfield      (1:ext      ,:)
        endif
      end if

      if ( use_GeoWind_L ) then
        ugeo500    (1-ext:0    ,:) = ugeo500    (ni-ext+1:ni,:)
        ugeo500    (ni+1:ni+ext,:) = ugeo500    (1:ext      ,:)
        vgeo500    (1-ext:0    ,:) = vgeo500    (ni-ext+1:ni,:)
        vgeo500    (ni+1:ni+ext,:) = vgeo500    (1:ext      ,:)
      end if
    end if

!print *,'ni:',ni
!print *,'pfield org:', pfield(   1:   4,593)
!print *,'pfield ext:', pfield(ni+1:ni+4,593)
!  print *,'pfield(1440:1442,593)',pfield(1440:1442,593)
!stop

    cfield = 0.0



!   Loop over whole sea level pressure field to locate centers
!   ==========================================================
!
    if (debug_L) print *,'Loop over whole sea level pressure field to locate centers'

    num_pc = 0
    pposi  = 0
    pposj  = 0
!

    ! Loop over all points in specified window
    do i=i_start,i_end
    do j=j_start,j_end

      if ( mask_L ) then 
        if ( mfield(i,j) .lt. 0.5 ) cycle                  ! If mask given and pont outside mask -> cycle
      endif
      if ( abs(glats(i,j)) .lt. 5. ) cycle                 ! Check that point is far enough from the equator
      if ( northern_hemi .and. glats(i,j) .lt. 0. ) cycle  ! If mask = northern hemisphere and point is in southern -> cycle
      if ( southern_hemi .and. glats(i,j) .gt. 0. ) cycle  ! If mask = southern hemisphere and point is in northern -> cycle
!      if (debug_L) print *,'First checks cleared'

      ! [modified by TC --->]
      ! A. When looking for pressure center
      !                     ---------------
      if ( c_field == 'PN' .or. c_field == 'PNS' ) then

        if ( pfield(i,j  ) .gt. pcrit ) cycle              ! If pressure greater than critical pressure -> cycle
        if ( pfield(i,j-1) .lt. pfield(i,j) ) cycle        ! If PN of point below is lower this one cannot be center -> cycle
        if ( pfield(i,j+1) .lt. pfield(i,j) ) cycle        ! If PN of point above is lower this one cannot be center -> cycle
        if ( minval(pfield(i-nps_i(j):i+nps_i(j),j-nps_j:j+nps_j)) .lt. pfield(i,j) ) cycle ! If there is any point in "inner square"
                                                                                            ! that fits in circle with radius 'distcc' -> cycle

        if (debug_L) print *,'A0 checks cleared'

        ! A1. Checking pfield: first find a circular region with a 'distcc' radius
        center_check = .true.
        do jj = j-np_j   , j+np_j
           j2 = int(((j+jj)/2) + 0.5 )
        do ii = i-np_i(jj), i+np_i(jj)

           ! Skip points in inner square since they already got checked above
           if ( i-nps_i(jj) <= ii .and. ii <= i+nps_i(jj) .and. j-nps_j <= jj .and. jj <= j+nps_j ) cycle

            call calc_dist (glats(i ,j ),glons(i ,j ), gxlats(ii,jj),gxlons(ii,jj), dist12)
!           w = sqrt((dist_i(j2)*abs(i-ii))**2 + (dist_j*abs(j-jj))**2 )
!if (i==100) print *,'calc_dist, points:',i-ii,j-jj,dist12,w,dist12-w
!if (abs(dist12-w) >= 30000.) print *,'calc_dist, points:',i,j,i-ii,j-jj,dist12,w,dist12-w
!if (abs(dist12-w) >=  5000. .and. j>100.and.j<619 ) print *,'calc_dist, points:',i,j,i-ii,j-jj,dist12,w,dist12-w
!if (abs(dist12-w) >= 1200. .and. j> 80.and.j<639 ) print *,'calc_dist, points:',i,j,i-ii,j-jj,dist12,w,dist12-w
!if (abs(dist12-w) >= 3000. .and. j> 40.and.j<679 ) print *,'calc_dist, points:',i,j,i-ii,j-jj,dist12,w,dist12-w
!if ( i==1440 .and. j==131 .and. j-jj==7 ) print *,i,j,i-ii,j-jj,ii,jj,glons(i ,j ),glons(ii,jj),gxlats(i ,j ),gxlats(ii,jj),dist12,w,dist12-w

           if ( dist12 .le. distcc*1000. ) then
              ! If any point in this region has a pressure lower than the center at (i,j), then this center point cannot be
              ! considered as the storm center
              if ( pfield(ii,jj) .lt. pfield(i,j) ) then
                  center_check = .false.
                  goto 400
              end if
           end if
        enddo   
        enddo  

400     if ( .not.center_check ) cycle
        if (debug_L) print *,'A1 check cleared' 

        ! A2. Checking vfield - if requested: 
        !     Among those centers fullfill the A1 critierion,
        !     the vorticity in at least one surronding point in a distcc circle must be stronger than vcrit
        if ( vcrit > 0. ) then

           ! Quick check in inner square
           ! Northern hemisphere
           if ( glats(i,j) .ge.  0. ) then
              if ( maxval(vfield(i-nps_i(j):i+nps_i(j),j-nps_j:j+nps_j)) .ge.  vcrit ) goto 420  ! Vorticity strong enough -> go to next check
           ! Southern hemisphere
           else
              if ( minval(vfield(i-nps_i(j):i+nps_i(j),j-nps_j:j+nps_j)) .le. -vcrit ) goto 420  ! Vorticity strong enough -> go to next check
           end if

           ! If no point was found in inner square, check vorticity in other points in circle
           do jj = j-np_j   , j+np_j
           do ii = i-np_i(jj), i+np_i(jj)

              ! Skip point in inner square since they already got checked in the quick check above
              if ( i-nps_i(jj) <= ii .and. ii <= i+nps_i(jj) .and. j-nps_j <= jj .and. jj <= j+nps_j ) cycle

              call calc_dist (glats(i ,j ),glons(i ,j ), gxlats(ii,jj),gxlons(ii,jj), dist12)
       
              if ( dist12 .le. distcc*1000. ) then
                 ! Check that vorticity in at least one surronding point in a distcc square is large enough
                 ! Northern hemisphere
                 if ( glats(i,j) .ge.  0. ) then
                    if ( vfield(ii,jj) .ge.  vcrit ) goto 420  ! Vorticity strong enough -> go to next check
                 ! Southern hemisphere
                 else
                    if ( vfield(ii,jj) .le. -vcrit ) goto 420  ! Vorticity strong enough -> go to next check
                 end if
               end if

           enddo
           enddo

           cycle     ! No point was found in circle with a strong enough vorticity -> cycle
420       continue   ! There is at least one point with a strong enough vorticity -> continue

          if (debug_L) print *,'A2 check cleared'

        endif


      ! B. When looking for vorticity center
      !                     ----------------
      else
      
        ! Northern hemisphere
        if ( glats(i,j) .ge.  0. ) then
          if ( vfield(i,j  ) .le. vcrit ) cycle            ! NH: If vort lower than critical vorticity -> cycle
          if ( vfield(i,j-1) .gt. vfield(i,j) ) cycle      ! NH: If vort of point above is higher this one cannot be center -> cycle
          if ( vfield(i,j+1) .gt. vfield(i,j) ) cycle      ! NH: If vort of point above is higher this one cannot be center -> cycle
        ! Southern hemisphere
        else
          if ( vfield(i,j  ) .ge. -vcrit ) cycle           ! SH: If vorticity greater than negative critical vorticity -> cycle
          if ( vfield(i,j-1) .lt. vfield(i,j) ) cycle      ! SH: If vort of point above is lower this one cannot be center -> cycle
          if ( vfield(i,j+1) .lt. vfield(i,j) ) cycle      ! SH: If vort of point above is lower this one cannot be center -> cycle
        endif 

        ! First find a circular region with 'distcc' radius
        center_check = .true.
        do jj = j-np_j,    j+np_j
        do ii = i-np_i(jj), i+np_i(jj)

           call calc_dist (glats(i ,j ),glons(i ,j ), gxlats(ii,jj),gxlons(ii,jj), dist12)

           ! B1. Checking vfiled: find the maximum vorticity as storm center
           if ( dist12 .le. distcc*1000. ) then
              ! Northern hemisphere
              if ( glats(i,j) .ge.  0. ) then
                ! If any point in this region has a vorticity larger than the center at (i,j), this center point
                ! cannot be considered as the storm center
                if ( vfield(ii,jj) .gt. vfield(i,j) ) then
                   center_check = .false.
                   goto 500
                end if
              ! Southern hemisphere
              else
                ! If any point in this region has a vorticity smaller (more negative) than the center at (i,j), this center point
                ! cannot be considered as the storm center
                if ( vfield(ii,jj) .lt. vfield(i,j) ) then
                   center_check = .false.
                   goto 500
                end if
              end if  
           end if

        enddo
        enddo

        ! B2. Checking vfield: among those centers fulfill the B1 critierion, the following condition has to 
        ! be met to be kept. 
        center_check = .false.
        do jj = j-np_j,    j+np_j
        do ii = i-np_i(jj), i+np_i(jj)
           if ( pfield(ii,jj) .le.  pcrit ) center_check = .true.           
        enddo
        enddo
500     if ( .not.center_check) cycle       

      end if
      ![<--- modified by TC]

      num_pc = num_pc + 1
      pposi(num_pc) = i
      pposj(num_pc) = j
        

!print *,'np_i,np_j for pressure minumum: ',np_i(jj),np_j
!if (counter == 4) print *,'Pressure minimum found',i,j,pfield(i,j),vfield(i,j),pfield_real(i,j)
!stop

    end do
    end do

    if (debug_L) print *,'Loop over points finished'
!    print *,'Date:',date, '  Centers found:',num_pc
!print*,'mask_L BBB:',mask_L


    ! If no centers were found write existing storms and go to next timestep
    if ( num_pc == 0 ) then

      ! Mark all storms as finished
      do t=1,last_track
        cfinished(t) = .true.
      end do

      !  Write each finished storm track into text output file
      if (debug_L) print *,'Call write_track because no centers were found'
      call write_track(.false.)

      ! Reset indices
      last_track = 0
      cpoints    = 0

    end if



!if (counter == 4) stop

!   Check for each extreema if it is far enough away ( more than 
!   'distcc' kilometers ) from any other extreema
    keep = .true.
    do pc=1,num_pc-1
      do pc2=pc+1,num_pc

        call calc_dist (glats(pposi(pc) ,pposj(pc) ),glons(pposi(pc) ,pposj(pc) ), &
                        glats(pposi(pc2),pposj(pc2)),glons(pposi(pc2),pposj(pc2)), dist12)
        dist12 = dist12 / 1000

        if ( dist12 .le. distcc ) then

          ! If looking for smooth pressure centers
          if ( p_field == 'PNS' ) then
            ! Keep point with lower real pressure and mark other for deletion
            if ( pfield_real(pposi(pc) ,pposj(pc)) .gt. &
                 pfield_real(pposi(pc2),pposj(pc2)) ) then
              keep(pc)  = .false.
            else
              keep(pc2) = .false.
            end if

          ! If looking for real pressure centers
          elseif ( p_field == 'PN' ) then
            ! Keep point with higher vorticity
            if ( abs(vfield(pposi(pc) ,pposj(pc))) .gt. &
                 abs(vfield(pposi(pc2),pposj(pc2))) ) then
              keep(pc)  = .false.
            else
              keep(pc2) = .false.
            end if

          ! If looking for vorticity centers
          else
            ! Keep point with lower pressure and mark other for deletion
            if ( pfield(pposi(pc) ,pposj(pc)) .gt. &
                 pfield(pposi(pc2),pposj(pc2)) ) then
              keep(pc)  = .false.
            else
              keep(pc2) = .false.
            end if
          end if

        end if
      end do
    end do


!   Write all centers found for this timestep
    if ( plot_centers_L ) then
      do pc=1,num_pc
        if ( keep(pc) ) cfield(pposi(pc),pposj(pc)) = 10.
!     if ( keep(pc) ) cfield(pposi(pc),pposj(pc)) = pfield(pposi(pc),pposj(pc))
      end do

      call plot_centers_write (cfield)
                   
    end if



!  ############################################################################



!  Start tracking the storms
!  =========================

  if (debug_L) print *,'Start tracking the storms'
!print*,'mask_L CCC:',mask_L

  pi = 4.0 * ATAN(1.D0)
  pmatch = 0


!  Calculate for each storm from the last time step
!  the probable position for this time step (p+1)
!  ------------------------------------------------

  do t=1,last_track
     tracks(t) = t
  end do

  last_s = last_track
  s      = 1

! Loop over all stormtracks already in array
! ------------------------------------------
  do while ( s .le. last_s )

    t = tracks(s)

    if (debug_L) print *,'track number:', s, t

    if ( cpoints(t) .eq. 0 ) then
      s = s + 1
      cycle  ! No centre in this storm track -> go to the next storm
    end if
    cmatch(t) = 0


!   Next position according to history
!   ----------------------------------
    w = weight
    p = cpoints(t)


!   Next position according to history
!   ----------------------------------
    dp = 1  ! Take only last two points into account
    dlonh = 0.
    dlath = 0.
    if ( cpoints(t) .gt. 1 ) then
      if     ( clon(p,t).gt.270. .and. clon(p-dp,t).lt.90. ) then
        dlonh = (360. - (clon(p,t) - clon(p-dp,t))) / dp
      elseif ( clon(p,t).lt.90. .and. clon(p-dp,t).gt.270. ) then
        dlonh = (360. + (clon(p,t) - clon(p-dp,t))) / dp
      else
        dlonh = (clon(p,t) - clon(p-dp,t)) / dp
      end if
      dlath = (clat(p,t) - clat(p-dp,t)) / dp
    end if


    if ( use_GeoWind_L ) then
!     Next position according to geostrophic wind
!     -------------------------------------------

      p1 = 1   ! Use method 1)-4) - see below "Loop over the four different methods."

      ! If point too close to equator -> do NOT use geostrophic wind!!!
      if ( abs(clat(p,t)) <= 20 ) then
        p1 = 3   ! Use only method 3)-4)

      else
        ! Calculate geostrophic wind average over np points (calculated from distcc)
        i = ci(p,t)
        j = cj(p,t)


        ! For "real" pressure, vorticity and wind strength check min resp. max 
        ! in an area with a diameter of 'distcc' around the center
        cugeo(p,t) = sum(ugeo500(i-np_i(j):i+np_i(j),j-np_j:j+np_j)) / ( (np_i(j)*2+1) * (np_j*2+1) )
        cvgeo(p,t) = sum(vgeo500(i-np_i(j):i+np_i(j),j-np_j:j+np_j)) / ( (np_i(j)*2+1) * (np_j*2+1) )

        dlonw = cugeo(p,t) * deltat / (2*pi*earthr) * 360. / cos(clat(p,t)*deg2rad)
        dlatw = cvgeo(p,t) * deltat * 360. / (2*pi*earthr)
      end if

    else
      ! Do not use geostrophic wind to predict location of next center
      p1 = 3   ! Use only method 3)-4) - see below "Loop over the four different methods."
    end if


    if (debug_L) print *,'Next point according to history:',dlath,dlonh
    if (debug_L) print *,'Next point according to wind   :',dlatw,dlonw


!   Final new positions ...
!   -----------------------

    ! Loop over the four different methods.
    ! Predict next position according to:
    ! 1) 500 hPa wind and history    (only when use_GeoWind_L=.true.)
    ! 2) just 500 hPa wind           (only when use_GeoWind_L=.true.)
    ! 3) just history
    ! 4) position of last point

    do pp=p1,4

      if (debug_L) print *,'Next position prediction number: ',pp
!print *,'Next position prediction number: ',pp

!if ( pp.eq.1 .or. pp.eq.2 ) cycle  ! Do not calculate next position according to wind

      if ( cmatch(t) .ne. 0 ) cycle  ! Match already found

      select case (pp)
        !  ... according to wind and history      
        case (1)
          if ( cpoints(t) .eq. 1 ) cycle
          clon(p+1,t) = clon(p,t) + w*dlonh + (1-w)*dlonw
          clat(p+1,t) = clat(p,t) + w*dlath + (1-w)*dlatw
        !  ... according to wind
        case (2)
          clon(p+1,t) = clon(p,t) + dlonw
          clat(p+1,t) = clat(p,t) + dlatw
        !  ... according to history
        case (3)
          if ( cpoints(t) .eq. 1 ) cycle
          clon(p+1,t) = clon(p,t) + dlonh
          clat(p+1,t) = clat(p,t) + dlath
        !  ... around last point
        case (4)
          clon(p+1,t) = clon(p,t)
          clat(p+1,t) = clat(p,t)
      end select


      if ( clat(p+1,t) .gt. 90 ) then
        clat(p+1,t) = 180 - clat(p+1,t)
        clon(p+1,t) = clon(p+1,t)  + 180
      end if
      if ( clat(p+1,t) .lt. -90 ) then
        clat(p+1,t) = -180 - clat(p+1,t)
        clon(p+1,t) = clon(p+1,t)  + 180
      end if

      if ( clon(p+1,t) .lt.   0. ) clon(p+1,t) = 360. + clon(p+1,t)
      if ( clon(p+1,t) .ge. 360. ) clon(p+1,t) = clon(p+1,t) - 360.

      ! Calculate distance between predicted continuation of track and last position
      call calc_dist (clat(p,t)  ,clon(p,t), clat(p+1,t),clon(p+1,t), cdist(t))


!     Check if there is a storm center in the current time step
!     which could be the continuation of this storm
!     ---------------------------------------------------------

      min_dist = 2*pi*earthr
      cfinished(t) = .true.

      if (debug_L) print *,'Loop over all storm centers of current time step'

!     Loop over all storm centers of current time step
      do pc=1,num_pc

        if ( .not.keep(pc) ) cycle

        i = pposi(pc)
        j = pposj(pc)


        ! Calculate distance between this center and the predicted next point of this storm
        call calc_dist (clat(p+1,t), clon(p+1,t), glats(i,j), glons(i,j)    , dist12)

        i1 = ci(p,t) - 1
        i2 = ci(p,t) + 1
        j1 = cj(p,t) - 1
        j2 = cj(p,t) + 1
        if (global_L) then
          if ( i1 .eq. 0 )    i1 = ni
          if ( i2 .eq. ni+1 ) i2 = 1
        else
          if ( i1 .eq. 0 )    i1 = 1
          if ( i2 .eq. ni+1 ) i2 = ni
        end if
        if ( j1 .eq. 0 )    j1 = 1
        if ( j2 .eq. nj+1 ) j2 = nj
 

!       dist = cdist(t)*4
        dist = max(cdist(t),disttr*1000)   ![modified by TC]

        ! See if this new center is close to the predicted next point of this storm
        if ( (   dist12  .le. dist                  .or.  &
               ( i.ge.i1 .and. i.le.i2              .and. &
                 j.ge.j1 .and. j.le.j2 )            .or.  &
               ( dist12 .le. dist*1.5               .and. &
                 cpres(p,t) .le. pfield(i,j)+3.     .and. &
                 cpres(p,t) .ge. pfield(i,j)-3. ) ) .and. &
                 dist12 .lt. min_dist ) then

          ! Center is possible continuation of this storm

          ! Center got already matched to another storm
          if ( pmatch(pc) .ne. 0 .and. &
               pmatch(pc) .ne. t ) then

            ! Check which predicted storm position is closer
            ! to this center
            t2 = pmatch(pc)
            call calc_dist (clat(cpoints(t2)+1,t2), &
                            clon(cpoints(t2)+1,t2), &
                            glats(i,j), glons(i,j)    , dist12a)

            !      Center fits better to older track
            !      so do not do anything
            if ( dist12 .ge. dist12a ) then
              cycle

            !      Center fits better to this track
            else

              cfinished(t) = .false.
              cfinished(pmatch(pc)) = .true.

              ! If another center was already matched to this storm
              ! free the other center
              if ( cmatch(t) .ne. 0 ) pmatch(cmatch(t)) = 0

              pmatch(pc) = t
              cmatch(t)  = pc
              min_dist = dist12

            !        To see if another center can be matched to the rejected storm
            !        redo center finding for the rejected storm. Therefore add it 
            !        again to the list of tracks to check

              last_s = last_s + 1
              tracks(last_s) = t2

            end if


          !    Center did not yet get matched to a storm
          else

!print *,' Center',pc,' matched to track',t

            ! If another center was already matched to this storm
            ! free the other center
            if ( cmatch(t) .ne. 0 ) pmatch(cmatch(t)) = 0
!if ( cmatch(t) .ne. 0 ) print *,'    => center',cmatch(t),' freed'

            pmatch(pc)   = t

            cmatch(t)    = pc
            min_dist     = dist12
  
            cfinished(t) = .false.

          end if

        end if

      end do ! End loop over different next point prediction methods

!print*,'mask_L CYZ:',mask_L
    end do ! End loop over new found centers

    s = s + 1  ! Next storm in array

!if ( s .gt. 10 ) stop ! Katja

!!!  goto 400
!print*,'mask_L CZZ:',mask_L
  enddo  ! End of while loop over storm tracks

!print*,'mask_L DDD:',mask_L
! End of loop over already existing, but not finished storm tracks



!  Check for each storm for which no new center could
!  be found if there is a not yet matched center which
!  might be the continuation of this storm
!  do t=1,last_track    
!    if ( .not. cfinished(t) ) cycle
!
!    do pc=1,num_pc
!      if ( pmatch(pc) ) cycle
!
!    end do
!
!  end do


!  print *,' pmatch = ', pmatch(1:num_pc)


!  Write each finished storm track into text output file
!  -----------------------------------------------------
  call write_track(.false.)


!print *,'cpoints(1:10):',cpoints(1:10)


!  Find new last_track
  do t=last_track,1,-1
    if ( cpoints(t) .ne. 0 ) then
      last_track = t
      exit
    end if
  end do

!print *,'last_track:',last_track



!  Write all new centers in track arrays
!  -------------------------------------
  do pc=1,num_pc

    if ( .not.keep(pc) ) cycle
  
!   Get position in track arrays
!   First center of a new storm
    if ( pmatch(pc) .eq. 0 ) then

!  Find first free position in track array
      do t=1,last_track+1
        if ( cpoints(t) .eq. 0 ) exit
      end do

!   Center is part of an already existing storm
    else
      t = pmatch(pc)

    end if

    if ( t .eq. last_track+1 ) last_track = last_track + 1

    if ( last_track .gt. maxStorms ) then
      print *,'Too many storms for array.'
      print *,'Increase parameter: maxStorms'
      print *,'    ===== ABORT ====='
      stop
    end if

    cpoints(t) = cpoints(t) + 1
    c = cpoints(t)

    i = pposi(pc)
    j = pposj(pc)


    ! For "real" pressure, vorticity and wind strength check min resp. max 
    ! in an area with a diameter of 'distcc' around the center

    ! Calculate wind strength if not read
    if ( plot_10mWind_L ) then
      if ( .not.UV_read_L ) then
        do jj = j-np_j,j+np_j
          do ii = i-np_i(jj),i+np_i(jj)
            wind_strength(ii,jj) = sqrt(uwfield(ii,jj)**2 + vwfield(ii,jj)**2)
          end do
        end do
      end if
    end if



!   Fill track arrays
!   -----------------
    ci(c,t) = i
    cj(c,t) = j
    cdate(c,t) = date*100 + time/10000

    clat(c,t) = glats(i,j)
    clon(c,t) = glons(i,j)

    ! Pressure & vorticity fields
    ! Pressure center
    if ( p_field == 'PNS' .or. p_field == 'PN' ) then
      ! Center pressure
      cpres(c,t) = pfield(i,j)
      ! Max vorticity in surrounding circular area [modified by TC --->]
      cvort(c,t) = vfield(i,j)
      do jj = j-np_j, j+np_j
      do ii = i-np_i(jj), i+np_i(jj)
           call calc_dist (glats(i ,j ),glons(i ,j ), gxlats(ii,jj),gxlons(ii,jj), dist12)
           if ( dist12 .le. distcc*1000. ) then
              if ( glats(i,j) .ge.  0. ) then
                 if (vfield(ii,jj) .gt. cvort(c,t) ) cvort(c,t) = vfield(ii,jj)   ! Northern hemisphere
              else
                 if (vfield(ii,jj) .lt. cvort(c,t) ) cvort(c,t) = vfield(ii,jj)   ! Southern hemisphere
              end if
           end if
      enddo
      enddo
      ! [<------]

    ! Vorticity center
    else
      ! Minimum real pressure in surrounding [modified by TC --->]
      cpres(c,t) = pfield(i,j)
      do jj = j-np_j, j+np_j
      do ii = i-np_i(jj), i+np_i(jj)
           call calc_dist (glats(i ,j ),glons(i ,j ), gxlats(ii,jj),gxlons(ii,jj), dist12)
           if ( dist12 .le. distcc*1000. ) then
              if (pfield(ii,jj) .lt. cpres(c,t) ) cpres(c,t) = pfield(ii,jj)
           end if
      enddo 
      enddo 
      ![<------]
      ! Center vorticity
      cvort(c,t) = vfield(i,j)
    end if

    ! Smooth pressure center: Find minimum real pressure as well
    if ( p_field == 'PNS' ) then
      ! Check for minimum pressure in original PN field in surrounding [modified by TC --->]
      cpres_real(c,t) = pfield_real(i,j)
      do jj = j-np_j, j+np_j
      do ii = i-np_i(jj), i+np_i(jj)
           call calc_dist (glats(i ,j ),glons(i ,j ), gxlats(ii,jj),gxlons(ii,jj), dist12)
           if ( dist12 .le. distcc*1000. ) then
              if (pfield_real(ii,jj) .lt. cpres_real(c,t) ) cpres_real(c,t) = pfield_real(ii,jj)
           end if
      enddo 
      enddo 
      ![<------]
    end if

    ! Calculate the VORSavg (vfield averaged over the circular region with 'distcc' radius)
      cvorta(c,t) = 0.
      ppoint = 0.
      do jj = j-np_j, j+np_j
      do ii = i-np_i(jj), i+np_i(jj)
           call calc_dist (glats(i ,j ),glons(i ,j ), gxlats(ii,jj),gxlons(ii,jj), dist12)
           if ( dist12 .le. distcc*1000. ) then
              ppoint=ppoint+1.
              cvorta(c,t) = cvorta(c,t)+vfield(ii,jj)
           end if
      enddo 
      enddo 
      if (ppoint.ne.0.)  cvorta(c,t)=cvorta(c,t)/ppoint

    ! Check for maximum wind strength surrounding area and
    if ( plot_10mWind_L ) cwind(c,t) = maxval(wind_strength(i-np_i(j):i+np_i(j),j-np_j:j+np_j))

!print *,'pfield,cpres,vfield,cvort:',pfield(i,j),cpres(c,t),vfield(i,j),cvort(c,t)
!print *,'pfield,cpres,cvort,cwind:',pfield(i,j),cpres(c,t),cvort(c,t),cwind(c,t)
!print *,'wind_strength:',wind_strength

  end do

!if (num_pc.ge.1) then
!print *,'STOP'
!stop
!end if


!  ############################################################################

    counter = counter + 1

  goto 200
  210 continue
   

!  Read next input file
!  --------------------

  ! Close previous input file
  call input_file_close (p_field, plot_10mWind_L)

  ! If last input file was read
  if ( f == f2 ) goto 110
 
  ! Increase input file counter and get name of next file
  f = f + 1
  ifile = get_filename(f)

  ! Read next input file
  call input_file_open (ifile, plot_10mWind_L)
  print *,''
  print *,' Now treating file = ', ifile(1:len_trim(ifile))
  print *,''

  goto 100

  110 continue


!  After the end of the last file:
!  ==============================
!  Write each finished storm track into text output file
!  -----------------------------------------------------
  call write_track(.true.)

  ! Close output text file
  close(unit=tun)


!  Write track density field
!  -------------------------
  if ( plot_tracks_L ) then
    if (debug_L) print *,'Write track density field'
    call plot_track_density (t_density, tdfile)
    if (debug_L) print *,'Track density field written'
  endif


  if ( plot_centers_L ) then
    call plot_centers_close ()
  end if

  deallocate (vfield, pfield, cfield)
  if ( mask_L )         deallocate (mfield)
  if ( plot_10mWind_L ) deallocate (uwfield, vwfield, wind_strength)
  if (  use_GeoWind_L ) deallocate (ugeo500, vgeo500)
  if ( plot_tracks_L  ) deallocate (t_density)
  deallocate (pposi, pposj, keep)
  deallocate (glats, glons)
 

!  print *,' pcrit  = ', pcrit
!  print *,' p_min  = ', p_min
!  print *,' vcrit  = ', vcrit
!  print *,' frame = ', frame
!  print *,' distcc = ', distcc
!  print *,' vorticity level : ',dummy(1:len_trim(dummy)),v_ip1


 1000 format (i8,x,i4,2(x,f7.2),4(x,1pe12.5))
! 1100 format (a30,4x,a10,4(7x,a6))
 1100 format (a29,8x,a18,3(7x,a6))
   



  contains

  ! =======================================================================

  subroutine write_track(finished)

!  Write each finished storm track into text output file
!  -----------------------------------------------------

    logical, intent(in) :: finished   ! .true. : all time steps have been read

!print *,'last_track:',last_track
    do t=1,last_track

!print *,'Check track:',t

      if ( .not.finished .and. .not.cfinished(t) ) cycle

      ! Only keep storms with a minimum number of centers
      if ( cpoints(t) .lt. min_centers ) then
        cpoints(t) = 0
        cycle
      end if

      ! Only keep storms with a minimum pressure below 'p_min'
      ! Find minimum pressure in track
      min_p = 9999.
      do c=1,cpoints(t)
        if ( p_field == 'PNS' ) then
          if ( cpres_real(c,t) .lt. min_p ) min_p = cpres_real(c,t)
        else
          if ( cpres(c,t) .lt. min_p ) min_p = cpres(c,t)
        end if
      end do
      if ( min_p .gt. p_min ) then
        cpoints(t) = 0
        cycle
      end if

      ! Only keep storms that travel at least 1000 km in their lifetime
      lon1 = clon(1,t)
      lat1 = clat(1,t)
      lon2 = clon(cpoints(t),t)
      lat2 = clat(cpoints(t),t)

      call calc_dist (clat(1,t), clon(1,t), clat(cpoints(t),t), clon(cpoints(t),t), dist)

      if ( dist .lt. span*1000. ) then
        cpoints(t) = 0
        cycle
      end if


      num_storms = num_storms + 1

      ! Write storm in output table with one or more of the following fields:
      !   smooth pressure, real pressure, vorticity(max), vorticity(avg), 10m wind

      print *,'Print storm track:', num_storms, 'with', cpoints(t), ' centers'

      ! Print smooth pressure and real pressure
      if ( c_field == 'PNS' ) then

        if ( plot_10mWind_L ) then
          if ( vcrit > 0. ) then
            ! Print: smooth pressure, real pressure, vorticity(max), vorticity(avg), 10m wind
            do c=1,cpoints(t)
              write(tun,1005) num_storms, c, ci(c,t), cj(c,t), cdate(c,t), clat(c,t), clon(c,t), &
                              cpres(c,t), cpres_real(c,t), cvort(c,t), cvorta(c,t), cwind(c,t)
            end do
          else
            ! Print: smooth pressure, real pressure,                                 10m wind
            do c=1,cpoints(t)
              write(tun,1003) num_storms, c, ci(c,t), cj(c,t), cdate(c,t), clat(c,t), clon(c,t), &
                              cpres(c,t), cpres_real(c,t),                          cwind(c,t)
            end do
          end if
        else
          if ( vcrit > 0. ) then
            ! Print: smooth pressure, real pressure, vorticity(max), vorticity(avg)
            do c=1,cpoints(t)
              write(tun,1004) num_storms, c, ci(c,t), cj(c,t), cdate(c,t), clat(c,t), clon(c,t), &
                              cpres(c,t), cpres_real(c,t), cvort(c,t), cvorta(c,t)
            end do
          else
            ! Print: smooth pressure, real pressure
            do c=1,cpoints(t)
              write(tun,1002) num_storms, c, ci(c,t), cj(c,t), cdate(c,t), clat(c,t), clon(c,t), &
                              cpres(c,t), cpres_real(c,t)
            end do
          end if
        end if

      ! Print only real pressure
      else

        if ( plot_10mWind_L ) then
          if ( vcrit > 0. ) then
            ! Print:         real pressure, vorticity(max), vorticity(avg), 10m wind
            do c=1,cpoints(t)
              write(tun,1004) num_storms, c, ci(c,t), cj(c,t), cdate(c,t), clat(c,t), clon(c,t), &
                              cpres(c,t), cvort(c,t), cvorta(c,t), cwind(c,t)
            end do
          else
            ! Print:         real pressure,                                 10m wind
            do c=1,cpoints(t)
              write(tun,1002) num_storms, c, ci(c,t), cj(c,t), cdate(c,t), clat(c,t), clon(c,t), &
                              cpres(c,t),                          cwind(c,t)
            end do
          end if
        else
          if ( vcrit > 0. ) then
            ! Print:         real pressure, vorticity(max), vorticity(avg), 10m wind
            do c=1,cpoints(t)
              write(tun,1003) num_storms, c, ci(c,t), cj(c,t), cdate(c,t), clat(c,t), clon(c,t), &
                            cpres(c,t), cvort(c,t), cvorta(c,t)
            end do
          else
            ! Print:         real pressure
            do c=1,cpoints(t)
              write(tun,1001) num_storms, c, ci(c,t), cj(c,t), cdate(c,t), clat(c,t), clon(c,t), &
                            cpres(c,t)
            end do
          end if
        end if

      end if


      !  Add track to track density field
      if ( plot_tracks_L ) then
        c = cpoints(t)
        if (debug_L) print *,'Call track_density'
        if (debug_L) print *,'Storm:',num_storms
        call track_density (t_density, ni, nj, c, global_L, ci(1:c,t), cj(1:c,t), glats, glons, num_storms)
      end if

      cpoints(t) = 0

    end do

! 1001 format (i8,x,i4,2(x,i3),x,i10,x,i8,2(x,f7.2),4(x,1pe12.5))
 1001 format (i8,x,i4,2(x,i4),x,i10,2(x,f7.2),2(x,1pe12.5),1(x,1pe12.5))
 1002 format (i8,x,i4,2(x,i4),x,i10,2(x,f7.2),2(x,1pe12.5),2(x,1pe12.5))
 1003 format (i8,x,i4,2(x,i4),x,i10,2(x,f7.2),2(x,1pe12.5),3(x,1pe12.5))
 1004 format (i8,x,i4,2(x,i4),x,i10,2(x,f7.2),2(x,1pe12.5),4(x,1pe12.5))
 1005 format (i8,x,i4,2(x,i4),x,i10,2(x,f7.2),2(x,1pe12.5),5(x,1pe12.5))

  end subroutine write_track

end program





! *************************************************************************
! *************************************************************************

! Subroutines
! ===========


subroutine calc_dist (lat1, lon1, lat2, lon2, dist12)
!
! Author
! Katja Winger (Oct 2008)
!
! Description
! Subroutine to calculate the distance in meters between
! two points (lat1,lon1) and (lat2,lon2) on the sphere
!

  implicit none

  real  lat1, lon1, lat2, lon2, dist12
  real  rlat1, rlon1, rlat2, rlon2
  real  x1(3), x2(3)
  real  d, pi, a

! Define some constants

! PI = 3.14159...
  pi = 2.*ASIN(1.)

! Mean radius of the Earth in meters
  a  = 6371.22E3

! Convert to radians
  rlon1=lon1
  rlon2=lon2
  if ( rlon1 .lt. 0 ) rlon1 = 360. + rlon1
  if ( rlon2 .lt. 0 ) rlon2 = 360. + rlon2

  rlat1=lat1*pi/180.
  rlon1=rlon1*pi/180.
  rlat2=lat2*pi/180.
  rlon2=rlon2*pi/180.

! Locate points in Cartesian space

  x1(1)=COS(rlat1)*COS(rlon1)
  x1(2)=COS(rlat1)*SIN(rlon1)
  x1(3)=SIN(rlat1)

  x2(1)=COS(rlat2)*COS(rlon2)
  x2(2)=COS(rlat2)*SIN(rlon2)
  x2(3)=SIN(rlat2)

! Find shortest distance in Cartesian space (divided by Earth's radius)

  d=SQRT((x1(1)-x2(1))**2+(x1(2)-x2(2))**2+(x1(3)-x2(3))**2)

! Find distance following Earth's surface

  dist12 = 2.*a*ASIN(d/2.)

  return
end


! ==============================================================================


subroutine track_density (t_density, ni, nj, points, global_L, ci, cj, lats, lons, t)
!
! Author
! Katja Winger (May 2007)
!
! Description
! Subroutine which adds a storm track to the track density field.
! Each center and each point closer than 200 km to the center is 
! counted to the track density. Also all points closer than 200 km 
! to a straight line drawn between two consecutive centers are counted. 
! Each point can be counted only once for one storm.
!
  implicit none

! I/O
  real      t_density(ni,nj)         ! Track density field to which current storm gets added
! I
  integer   ni, nj
  integer   points                   ! number of centers of current storm
  logical   global_L
  integer   ci(points), cj(points)   ! i and j positions of all centers of current storm
  real      lats(ni,nj), lons(ni,nj), lat1, lon1, lat0, lon0

  integer   density(ni,nj)
  integer   c, i, j, t

! Variables used to mark grids "around" the centers
  real      dist12
  integer   i0, j0, i_inc, j_inc

! Variables used to mark grids "along" the track
  integer   i1, j1, num_points, p, di,dj
  real      a, b, x, y

! ------------------------------------------------------------

!print *,'Plot storm track:', t, 'with', points, ' points'
!  print *,' ci :',ci
!  print *,' cj :',cj

  density = 0

  ! Loop over all points in track
  ! -----------------------------
  do c=1,points
!  do c=1,1

    ! Mark center point
!    density(ci(c),cj(c)) = 1

!print *,'density: i,j: ', ci(c),cj(c)

!cc   !!!!!!!!!!!!!!!!!!!!!
!    t_density(ci(c),cj(c)) = t_density(ci(c),cj(c)) + 1
!  end do
!  return
!cc   !!!!!!!!!!!!!!!!!!!!!

    ! Loop over the center point and 
    ! all points between this one and the previous center
    ! ---------------------------------------------------

    ! Determine number of points to loop over
    ! Last point
    if ( c == points ) then
      num_points = 1 
    else
      num_points = max( abs(ci(c)-ci(c+1)), abs(cj(c)-cj(c+1)) )
    end if

num_points = 1
!print *,'c, num_points:',c,num_points
!print *,'ci(c), ci(c+1):',ci(c), ci(c+1)
!print *,'cj(c), cj(c+1):',cj(c), cj(c+1)

    do p = 1,num_points
      ! p == 1 -> center point
      if ( p == 1 ) then
        i0 = ci(c)
        j0 = cj(c)
        di = ci(c+1)-ci(c)
        dj = cj(c+1)-cj(c)
      ! Points on line between two centers
      else

        i0 = ci(c) + (p-1)*di/num_points
        j0 = cj(c) + (p-1)*dj/num_points

        
      end if

!print *,'i0,j0,di,dj:',i0,j0,di,dj

      ! Mark center point and points on line
!      density(i0,j0) = 1
      t_density(i0,j0) = t

    end do
!stop

  end do

!print *,'t:',t
!  t_density = t_density + density*t

  return

end subroutine track_density

! ==============================================================================


subroutine get_window (global_L, frame_i, frame_j,       &
                       lon_W, lon_E, lat_S, lat_N, &
                       glats, glons, ni, nj,       &
                       i_start, j_start, i_end, j_end)

!
! Author
! Katja Winger (nov 2019)
!
! Description
! Determines indicies of borders for window in which to check storms

  implicit none

  logical         , intent(in)  :: global_L
  real            , intent(in)  :: lon_W, lon_E, lat_S, lat_N
  real            , intent(in)  :: glats(ni,nj), glons(ni,nj)
  integer         , intent(in)  :: ni, nj, frame_i, frame_j
  integer         , intent(out) :: i_start,j_start,i_end,j_end

  ! Local variables
  logical              :: keep_going, set_L
  integer              :: i_start_win,j_start_win,i_end_win,j_end_win
  integer              :: i, j, i0, j0, i1, j1
  real                 :: dist12
 

  print *,'Get window'
print *,'frame_i, frame_j:',frame_i, frame_j
 
  ! Determine minimum frame
  ! -----------------------

  i_start = frame_i + 1
  i_end   = ni - frame_i
  j_start = frame_j + 1
  j_end   = nj - frame_j

  if ( global_L ) then
    i_start = 1
    i_end   = ni
!    j_start = 2
!    j_end   = nj-1
  end if


  ! If a lat-lon window was specified
  ! ---------------------------------

  if ( lon_W .ne. 0. .or. &
       lon_E .ne. 0. .or. &
       lat_N .ne. 0. .or. &
       lat_S .ne. 0. ) then

    print *,'Window was specified:'
    print *,'lon_W,lon_E,lat_S,lat_N:',lon_W,lon_E,lat_S,lat_N

!    if ( lon_W .ge. 180. ) lon_W = lon_W - 360.

    ! South border
    j_start_win = 1
    do j=2,nj
      if ( glats(1,j) .gt. lat_S ) then
        j_start_win = j-1
        exit
      end if
    end do
    ! North border
    j_end_win = nj
    do j=nj-1,1,-1
      if ( glats(1,j) .lt. lat_N ) then
        j_end_win = j+1
        exit
      end if
    end do
    ! West border
    set_L = .false.
    i_start_win = 1
    do i=2,ni
!print *,'glons:',glons(i,1)
      if (.not. set_L .and. glons(i,1) .gt. lon_W ) then
        i_start_win = i-1
        set_L = .true.
!print *,'Set i_start_win =',i_start_win
      end if
      if ( set_L .and. glons(i,1) .lt. lon_W ) set_L = .false.
    end do
    ! East border
    i_end_win = ni
    do i=ni-1,1,-1
      if ( glons(i,1) .lt. lon_E ) then
        i_end_win = i+1
        exit
      end if
    end do

    ! Window not passing Greenwich
!    if ( lon_W .lt. lon_E ) then

    ! Window passing Greenwich
!    else

!    end if

    i_start = max(i_start, i_start_win)
    i_end   = min(i_end  , i_end_win)
    j_start = max(j_start, j_start_win)
    j_end   = min(j_end  , j_end_win)

  end if ! window was specified


print *,'ni, nj:',ni, nj
print *,'global:',global_L
print *,'i_start,i_end:',i_start,i_end
print *,'j_start,j_end:',j_start,j_end
!stop
end subroutine get_window

